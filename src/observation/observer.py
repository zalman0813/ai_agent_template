"""Core observer for LangGraph agent streaming.

Uses LangGraph's stream() API with multiple stream modes to capture
all execution events in real-time.
"""

import asyncio
from typing import Any

from langchain_core.messages import AIMessage, ToolMessage
from langgraph.graph.state import CompiledStateGraph

from src.errors import classify_error
from src.observation.outputs import OutputHandler


class AgentObserver:
    """Observes LangGraph agent execution via streaming.

    Example:
        ```python
        observer = AgentObserver([
            ConsoleOutput(),
            JsonFileOutput("logs/run.json"),
            CallbackOutput(my_ui_callback),
        ])

        result = observer.run(agent, {"messages": [...]})
        ```
    """

    def __init__(self, outputs: list[OutputHandler] | None = None):
        """Initialize observer with output handlers.

        Args:
            outputs: List of output handlers. Uses ConsoleOutput() if None.
        """
        from src.observation.outputs import ConsoleOutput

        self.outputs = outputs or [ConsoleOutput()]

    def emit(self, event_type: str, data: dict[str, Any]) -> None:
        """Emit event to all output handlers."""
        for output in self.outputs:
            try:
                output.emit(event_type, data)
            except Exception as e:
                print(f"[Observer] Output error: {e}")

    def run(
        self,
        agent: CompiledStateGraph,
        inputs: dict[str, Any],
        config: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Run agent with observation.

        Args:
            agent: Compiled LangGraph agent
            inputs: Input state for the agent
            config: Optional LangGraph config

        Returns:
            Final agent state
        """
        final_state = None
        current_node = None

        for chunk in agent.stream(
            inputs,
            config=config,
            stream_mode=["updates", "messages"],
        ):
            if isinstance(chunk, tuple):
                mode, data = chunk
                self._handle_stream_chunk(mode, data, current_node)

                if mode == "updates" and isinstance(data, dict):
                    for node_name in data.keys():
                        current_node = node_name
                        final_state = data[node_name]
            else:
                self._handle_stream_chunk("updates", chunk, current_node)
                if isinstance(chunk, dict):
                    for node_name in chunk.keys():
                        current_node = node_name
                        final_state = chunk[node_name]

        for output in self.outputs:
            output.close()

        return final_state or {}

    async def arun(
        self,
        agent: CompiledStateGraph,
        inputs: dict[str, Any],
        config: dict[str, Any] | None = None,
        max_retries: int = 2,
        retry_delay: float = 1.0,
    ) -> dict[str, Any]:
        """Async version of run() with retry logic.

        Args:
            agent: Compiled LangGraph agent
            inputs: Input state for the agent
            config: Optional LangGraph config
            max_retries: Maximum retry attempts for retryable errors
            retry_delay: Base delay between retries (doubles each retry)

        Returns:
            Final agent state, or dict with "error" key on failure
        """
        last_error = None

        for attempt in range(max_retries + 1):
            try:
                return await self._arun_stream(agent, inputs, config)
            except Exception as e:
                llm_error = classify_error(e)
                last_error = llm_error

                # Emit error event for UI feedback
                self.emit(
                    "error",
                    {
                        "message": llm_error.message,
                        "category": llm_error.category.value,
                        "attempt": attempt + 1,
                        "max_attempts": max_retries + 1,
                        "retryable": llm_error.retryable,
                    },
                )

                if not llm_error.retryable or attempt >= max_retries:
                    break

                # Exponential backoff
                delay = retry_delay * (2**attempt)
                await asyncio.sleep(delay)

        for output in self.outputs:
            output.close()

        # Return state with error info (graceful failure)
        return {"error": last_error.to_dict() if last_error else None}

    async def _arun_stream(
        self,
        agent: CompiledStateGraph,
        inputs: dict[str, Any],
        config: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Internal stream processing with empty stream detection."""
        final_state = None
        current_node = None
        chunk_count = 0

        async for chunk in agent.astream(
            inputs,
            config=config,
            stream_mode=["updates", "messages"],
        ):
            chunk_count += 1
            if isinstance(chunk, tuple):
                mode, data = chunk
                self._handle_stream_chunk(mode, data, current_node)

                if mode == "updates" and isinstance(data, dict):
                    for node_name in data.keys():
                        current_node = node_name
                        final_state = data[node_name]
            else:
                self._handle_stream_chunk("updates", chunk, current_node)
                if isinstance(chunk, dict):
                    for node_name in chunk.keys():
                        current_node = node_name
                        final_state = chunk[node_name]

        # Handle empty stream - trigger retry
        if chunk_count == 0:
            raise RuntimeError("No generations found in stream")

        for output in self.outputs:
            output.close()

        return final_state or {}

    def _handle_stream_chunk(
        self,
        mode: str,
        data: Any,
        current_node: str | None,
    ) -> None:
        """Process a stream chunk and emit appropriate events."""
        if mode == "messages":
            self._handle_messages_chunk(data)
        elif mode == "updates":
            self._handle_updates_chunk(data)

    def _handle_messages_chunk(self, data: Any) -> None:
        """Handle messages stream mode (LLM tokens)."""
        if isinstance(data, tuple) and len(data) == 2:
            message_chunk, metadata = data

            if hasattr(message_chunk, "content") and message_chunk.content:
                content = message_chunk.content
                token = self._extract_token_from_content(content)
                if token:
                    self.emit("llm_token", {"token": token})

    def _extract_token_from_content(self, content: Any) -> str | None:
        """Extract token string from various content formats.

        Handles:
        - String content (standard format)
        - List of content blocks (Anthropic format):
          [{"text": "...", "type": "text", "index": 0}]
        """
        if isinstance(content, str):
            return content if content else None

        if isinstance(content, list):
            # Anthropic returns content as list of blocks
            texts = []
            for block in content:
                if isinstance(block, dict) and block.get("type") == "text":
                    text = block.get("text", "")
                    if text:
                        texts.append(text)
            return "".join(texts) if texts else None

        return None

    def _handle_updates_chunk(self, data: dict[str, Any]) -> None:
        """Handle updates stream mode (node execution)."""
        if not isinstance(data, dict):
            return

        for node_name, node_output in data.items():
            self.emit("node_start", {"node": node_name})

            if isinstance(node_output, dict) and "messages" in node_output:
                messages = node_output["messages"]
                if not isinstance(messages, list):
                    messages = [messages]

                for msg in messages:
                    self._process_message(msg)

            self.emit("node_end", {"node": node_name})

    def _process_message(self, msg: Any) -> None:
        """Process a message and emit relevant events."""
        if isinstance(msg, AIMessage):
            if msg.tool_calls:
                for tool_call in msg.tool_calls:
                    self.emit("tool_call", {
                        "tool": tool_call.get("name"),
                        "args": tool_call.get("args", {}),
                        "id": tool_call.get("id"),
                    })
            elif msg.content:
                # Convert content to string (handles both OpenAI string and Anthropic list formats)
                content_str = self._extract_token_from_content(msg.content) or ""
                self.emit("llm_end", {"content": content_str})

        elif isinstance(msg, ToolMessage):
            self.emit("tool_result", {
                "tool": msg.name,
                "result": msg.content,
                "tool_call_id": msg.tool_call_id,
            })
