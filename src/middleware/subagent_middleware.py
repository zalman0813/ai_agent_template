"""Custom SubAgent Middleware implementation.

This middleware provides subagent capabilities using compile-time resolution.
Follows official LangChain SubAgentMiddleware pattern with added trace event support.

Architecture:
- Domain Layer: SubAgentSpec (type definition)
- Infrastructure Layer: CustomSubAgentMiddleware (LangChain integration + trace events)
"""

import asyncio
from collections.abc import Awaitable, Callable, Sequence
from typing import TYPE_CHECKING, Any, NotRequired, TypedDict

from langchain.agents import create_agent
from langchain.agents.middleware.types import (
    AgentMiddleware,
    ModelRequest,
    ModelResponse,
)
from langchain.tools import ToolRuntime
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, ToolMessage
from langchain_core.runnables import Runnable
from langchain_core.tools import BaseTool, StructuredTool
from langgraph.types import Command

if TYPE_CHECKING:
    from src.observation.outputs import OutputHandler


# ==================== Domain Layer ====================


class SubAgentSpec(TypedDict):
    """SubAgent specification for compile-time resolution.

    Supports both compile-time configuration and pre-compiled runnables.
    """

    name: str
    """The unique identifier for this subagent."""

    description: str
    """Description shown to main agent for deciding when to use this subagent."""

    # Pre-compiled runnable (if provided, ignores other configuration)
    runnable: NotRequired[Runnable]
    """Optional pre-compiled runnable. If provided, other config is ignored."""

    # Compile-time configuration (optional overrides)
    system_prompt: NotRequired[str]
    """System prompt for the subagent. Defaults to GENERAL_PURPOSE_SYSTEM_PROMPT."""

    tools: NotRequired[Sequence[BaseTool | Callable | dict[str, Any]]]
    """Explicit tools for this subagent. Defaults to default_tools."""

    middleware: NotRequired[list[AgentMiddleware]]
    """Middleware for this subagent. Defaults to default_middleware."""

    model: NotRequired[BaseChatModel]
    """Model for this subagent. Defaults to default_model."""


# State keys to exclude when passing state to subagents
_EXCLUDED_STATE_KEYS = {"messages", "todos", "structured_response"}


# ==================== Helper Functions ====================


def _get_message_text(msg) -> str:
    """Safely extract text from any message type.

    Handles AIMessage (.text), ToolMessage (.content), and various content formats
    including Anthropic-style content blocks.
    """
    if msg is None:
        return ""
    # AIMessage has .text property
    if hasattr(msg, "text"):
        return msg.text or ""
    # ToolMessage and others have .content
    if hasattr(msg, "content"):
        content = msg.content
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            # Handle content blocks (e.g., Anthropic format)
            return "".join(
                block.get("text", "") if isinstance(block, dict) else str(block)
                for block in content
            )
    return ""


def _get_final_message_text(result: dict) -> str:
    """Safely extract text from the last message in result.

    Returns empty string if result has no messages or extraction fails.
    """
    messages = result.get("messages")
    if not messages:
        return ""
    last_msg = messages[-1] if isinstance(messages, list) else messages
    return _get_message_text(last_msg)


# ==================== Constants ====================


# Default system prompt explaining task tool usage
TASK_SYSTEM_PROMPT = """## `task` (subagent spawner)

You have access to a `task` tool to launch short-lived subagents that handle isolated tasks. These agents are ephemeral — they live only for the duration of the task and return a single result.

When to use the task tool:
- When a task is complex and multi-step, and can be fully delegated in isolation
- When a task is independent of other tasks and can run in parallel
- When a task requires focused reasoning or heavy token/context usage that would bloat the orchestrator thread
- When sandboxing improves reliability (e.g. code execution, structured searches, data formatting)
- When you only care about the output of the subagent, and not the intermediate steps (ex. performing a lot of research and then returned a synthesized report, performing a series of computations or lookups to achieve a concise, relevant answer.)

Subagent lifecycle:
1. **Spawn** → Provide clear role, instructions, and expected output
2. **Run** → The subagent completes the task autonomously
3. **Return** → The subagent provides a single structured result
4. **Reconcile** → Incorporate or synthesize the result into the main thread

When NOT to use the task tool:
- If you need to see the intermediate reasoning or steps after the subagent has completed (the task tool hides them)
- If the task is trivial (a few tool calls or simple lookup)
- If delegating does not reduce token usage, complexity, or context switching
- If splitting would add latency without benefit

## Important Task Tool Usage Notes to Remember
- Whenever possible, parallelize the work that you do. This is true for both tool_calls, and for tasks. Whenever you have independent steps to complete - make tool_calls, or kick off tasks (subagents) in parallel to accomplish them faster. This saves time for the user, which is incredibly important.
- Remember to use the `task` tool to silo independent tasks within a multi-part objective.
- You should use the `task` tool whenever you have a complex task that will take multiple steps, and is independent from other tasks that the agent needs to complete. These agents are highly competent and efficient."""

# Template for task tool description
TASK_TOOL_DESCRIPTION = """Launch a subagent to handle complex, isolated tasks.

Available subagent types:
{available_agents}

Usage:
- subagent_type: Select which agent type to use
- description: Detailed task description and expected output format

Each subagent invocation is stateless - provide complete instructions."""

# System prompt for general-purpose subagent
GENERAL_PURPOSE_SYSTEM_PROMPT = """You are a general-purpose subagent with full access to all available tools.

## Your Role

You are spawned by a main agent to handle complex, multi-step tasks autonomously. You have access to the same tools as the main agent, making you the most capable subagent for tasks requiring:
- Complex reasoning across multiple steps
- Research and exploration followed by execution
- File operations, code modifications, or data processing
- Tasks that benefit from isolated context

## Execution Model

1. **Autonomous Execution**: Complete the entire task without user interaction
2. **Return Results**: Provide a clear, structured response when done
3. **No Nesting**: You cannot spawn other subagents - complete the work yourself

## Working with Skills

When skills are available in the context:
1. Read the skill documentation (SKILL.md) to understand capabilities
2. Use skill scripts via execute() when provided
3. Some operations REQUIRE script execution (cryptographic hashing, binary processing)

## Task Completion Guidelines

1. **Be Thorough**: Complete all aspects of the assigned task
2. **Be Efficient**: Minimize unnecessary steps while ensuring quality
3. **Be Clear**: Structure your final response for easy consumption by the main agent
4. **Handle Errors**: If something fails, explain what happened and what was attempted

## Output Format

When completing your task, provide:
1. **Summary**: Brief overview of what was accomplished
2. **Details**: Key findings, results, or changes made
3. **Next Steps** (if applicable): Any follow-up actions recommended"""


# ==================== Infrastructure Layer ====================


class CustomSubAgentMiddleware(AgentMiddleware):
    """Middleware that provides subagent capabilities via a `task` tool.

    Uses compile-time resolution: subagents are created during initialization
    using explicit default_model, default_tools, and default_middleware.

    Key features:
    - Compile-time agent creation (no runtime resolution)
    - Support for pre-compiled runnables
    - Optional trace event streaming for visibility
    - Clean, simple API following official patterns

    Example:
        ```python
        subagent_middleware = CustomSubAgentMiddleware(
            default_model=model,
            default_tools=[read_file, write_file, execute],
            default_middleware=[SummarizationMiddleware(...)],
            include_general_purpose=True,
            stream_subagent_events=True,
            output_handlers=[trace_handler],
        )
        ```
    """

    def __init__(
        self,
        *,
        default_model: BaseChatModel,
        default_tools: Sequence[BaseTool | Callable | dict[str, Any]] | None = None,
        default_middleware: list[AgentMiddleware] | None = None,
        subagents: list[SubAgentSpec] | None = None,
        system_prompt: str | None = TASK_SYSTEM_PROMPT,
        include_general_purpose: bool = True,
        task_description: str | None = None,
        stream_subagent_events: bool = False,
        output_handlers: list["OutputHandler"] | None = None,
        subagent_recursion_limit: int = 150,
    ) -> None:
        """Initialize the SubAgent Middleware.

        Args:
            default_model: Model for subagents (required).
            default_tools: Default tools for subagents.
            default_middleware: Default middleware for subagents.
            subagents: List of custom subagent specifications.
            system_prompt: System prompt addition explaining task tool usage.
                Set to None to disable prompt injection.
            include_general_purpose: Whether to include a general-purpose subagent.
            task_description: Custom description for the task tool.
            stream_subagent_events: Whether to emit subagent_start/end events.
            output_handlers: Output handlers to receive subagent events.
            subagent_recursion_limit: Max steps for subagent execution (default 150).
        """
        super().__init__()
        self._default_model = default_model
        self._default_tools = list(default_tools) if default_tools else []
        self._default_middleware = list(default_middleware) if default_middleware else []
        self._specs = subagents or []
        self._include_general_purpose = include_general_purpose
        self._system_prompt = system_prompt
        self._stream_subagent_events = stream_subagent_events
        self._output_handlers = output_handlers
        self._subagent_recursion_limit = subagent_recursion_limit

        # Compile subagents at initialization time
        self._compiled_subagents = self._compile_subagents()

        # Build descriptions for task tool
        descriptions = self._build_descriptions()
        description_str = "\n".join(descriptions)

        # Build tool description
        if task_description is None:
            tool_description = TASK_TOOL_DESCRIPTION.format(
                available_agents=description_str
            )
        elif "{available_agents}" in task_description:
            tool_description = task_description.format(available_agents=description_str)
        else:
            tool_description = task_description

        # Create the task tool
        self.tools = [self._create_task_tool(tool_description)]

    def _compile_subagents(self) -> dict[str, Runnable]:
        """Compile all subagents at initialization time."""
        compiled = {}

        # Compile general-purpose subagent if enabled
        if self._include_general_purpose:
            compiled["general-purpose"] = create_agent(
                self._default_model,
                system_prompt=GENERAL_PURPOSE_SYSTEM_PROMPT,
                tools=self._default_tools,
                middleware=self._default_middleware,
            )

        # Compile custom subagents
        for spec in self._specs:
            if "runnable" in spec:
                # Use pre-compiled runnable
                compiled[spec["name"]] = spec["runnable"]
            else:
                # Compile from spec with defaults
                compiled[spec["name"]] = create_agent(
                    spec.get("model") or self._default_model,
                    system_prompt=spec.get("system_prompt", GENERAL_PURPOSE_SYSTEM_PROMPT),
                    tools=spec.get("tools") or self._default_tools,
                    middleware=spec.get("middleware") or self._default_middleware,
                )

        return compiled

    def _build_descriptions(self) -> list[str]:
        """Build description list for task tool."""
        descriptions = []

        if self._include_general_purpose:
            descriptions.append(
                "- general-purpose: General-purpose agent for research and multi-step tasks"
            )

        for spec in self._specs:
            descriptions.append(f"- {spec['name']}: {spec['description']}")

        return descriptions

    def _emit_event(self, event_type: str, data: dict[str, Any]) -> None:
        """Emit event to all output handlers."""
        if not self._stream_subagent_events or not self._output_handlers:
            return
        for handler in self._output_handlers:
            try:
                handler.emit(event_type, data)
            except Exception:
                pass  # Silently ignore handler errors

    def _create_task_tool(self, description: str) -> BaseTool:
        """Create the task tool with compiled subagents."""
        compiled = self._compiled_subagents
        recursion_limit = self._subagent_recursion_limit

        # Closures for helper methods
        emit_event = self._emit_event
        stream_events = self._stream_subagent_events
        output_handlers = self._output_handlers

        def _prepare_subagent_state(
            description: str,
            runtime: ToolRuntime,
        ) -> dict:
            """Prepare state for subagent invocation."""
            subagent_state = {
                k: v
                for k, v in runtime.state.items()
                if k not in _EXCLUDED_STATE_KEYS
            }
            subagent_state["messages"] = [HumanMessage(content=description)]
            return subagent_state

        def _create_command_from_result(
            result: dict,
            tool_call_id: str,
        ) -> Command:
            """Create Command with state update from subagent result."""
            state_update = {
                k: v for k, v in result.items() if k not in _EXCLUDED_STATE_KEYS
            }
            final_text = _get_final_message_text(result)
            return Command(
                update={
                    **state_update,
                    "messages": [
                        ToolMessage(
                            final_text or "Task completed.",
                            tool_call_id=tool_call_id,
                        )
                    ],
                }
            )

        def _stream_subagent_with_events(
            subagent: Runnable,
            state: dict,
            subagent_name: str,
        ) -> dict:
            """Stream subagent execution and emit tool events."""
            from langchain_core.messages import AIMessage as AIMsg
            from langchain_core.messages import ToolMessage as ToolMsg

            subagent_config = {"recursion_limit": recursion_limit}
            accumulated_messages = []
            other_state = {}

            for chunk in subagent.stream(
                state, config=subagent_config, stream_mode=["updates", "messages"]
            ):
                if isinstance(chunk, tuple):
                    mode, data = chunk
                    if mode == "updates" and isinstance(data, dict):
                        for node_name, node_output in data.items():
                            if isinstance(node_output, dict):
                                if "messages" in node_output:
                                    messages = node_output["messages"]
                                    if not isinstance(messages, list):
                                        messages = [messages]
                                    accumulated_messages.extend(messages)
                                    for msg in messages:
                                        if isinstance(msg, AIMsg) and msg.tool_calls:
                                            for tool_call in msg.tool_calls:
                                                emit_event(
                                                    "subagent_tool_call",
                                                    {
                                                        "subagent_name": subagent_name,
                                                        "tool": tool_call.get("name"),
                                                        "args": tool_call.get(
                                                            "args", {}
                                                        ),
                                                        "id": tool_call.get("id"),
                                                    },
                                                )
                                        elif isinstance(msg, ToolMsg):
                                            emit_event(
                                                "subagent_tool_result",
                                                {
                                                    "subagent_name": subagent_name,
                                                    "tool": msg.name,
                                                    "result": (
                                                        msg.content[:500]
                                                        if msg.content
                                                        else ""
                                                    ),
                                                    "tool_call_id": msg.tool_call_id,
                                                },
                                            )
                                for k, v in node_output.items():
                                    if k != "messages":
                                        other_state[k] = v

            result = {**other_state}
            if accumulated_messages:
                result["messages"] = accumulated_messages
            return result

        async def _astream_subagent_with_events(
            subagent: Runnable,
            state: dict,
            subagent_name: str,
            max_retries: int = 1,
        ) -> dict:
            """Async stream subagent execution with retry logic."""
            from langchain_core.messages import AIMessage as AIMsg
            from langchain_core.messages import ToolMessage as ToolMsg

            from src.errors import classify_error

            subagent_config = {"recursion_limit": recursion_limit}
            for attempt in range(max_retries + 1):
                try:
                    accumulated_messages = []
                    other_state = {}
                    chunk_count = 0

                    async for chunk in subagent.astream(
                        state,
                        config=subagent_config,
                        stream_mode=["updates", "messages"],
                    ):
                        chunk_count += 1
                        if isinstance(chunk, tuple):
                            mode, data = chunk
                            if mode == "updates" and isinstance(data, dict):
                                for node_name, node_output in data.items():
                                    if isinstance(node_output, dict):
                                        if "messages" in node_output:
                                            messages = node_output["messages"]
                                            if not isinstance(messages, list):
                                                messages = [messages]
                                            accumulated_messages.extend(messages)
                                            for msg in messages:
                                                if (
                                                    isinstance(msg, AIMsg)
                                                    and msg.tool_calls
                                                ):
                                                    for tool_call in msg.tool_calls:
                                                        emit_event(
                                                            "subagent_tool_call",
                                                            {
                                                                "subagent_name": subagent_name,
                                                                "tool": tool_call.get(
                                                                    "name"
                                                                ),
                                                                "args": tool_call.get(
                                                                    "args", {}
                                                                ),
                                                                "id": tool_call.get(
                                                                    "id"
                                                                ),
                                                            },
                                                        )
                                                elif isinstance(msg, ToolMsg):
                                                    emit_event(
                                                        "subagent_tool_result",
                                                        {
                                                            "subagent_name": subagent_name,
                                                            "tool": msg.name,
                                                            "result": (
                                                                msg.content[:500]
                                                                if msg.content
                                                                else ""
                                                            ),
                                                            "tool_call_id": msg.tool_call_id,
                                                        },
                                                    )
                                        for k, v in node_output.items():
                                            if k != "messages":
                                                other_state[k] = v

                    if chunk_count == 0:
                        raise RuntimeError("No generations found in stream")

                    result = {**other_state}
                    if accumulated_messages:
                        result["messages"] = accumulated_messages
                    return result

                except Exception as e:
                    llm_error = classify_error(e)

                    emit_event(
                        "subagent_error",
                        {
                            "subagent_name": subagent_name,
                            "message": llm_error.message,
                            "attempt": attempt + 1,
                            "retryable": llm_error.retryable,
                        },
                    )

                    if not llm_error.retryable or attempt >= max_retries:
                        from langchain_core.messages import AIMessage

                        return {
                            "messages": [
                                AIMessage(
                                    content=f"SubAgent '{subagent_name}' error: {llm_error.message}",
                                )
                            ]
                        }

                    await asyncio.sleep(1.0 * (attempt + 1))

            return {}

        def task(
            description: str,
            subagent_type: str,
            runtime: ToolRuntime,
        ) -> str | Command:
            """Invoke a subagent synchronously."""
            # Get compiled subagent
            subagent = compiled.get(subagent_type)
            if subagent is None:
                available = list(compiled.keys())
                return f"Unknown subagent type '{subagent_type}'. Available: {', '.join(available)}"

            # Emit subagent_start event
            emit_event(
                "subagent_start",
                {
                    "name": subagent_type,
                    "description": description,
                },
            )

            state = _prepare_subagent_state(description, runtime)

            # Execute subagent
            subagent_config = {"recursion_limit": recursion_limit}
            if stream_events and output_handlers:
                result = _stream_subagent_with_events(subagent, state, subagent_type)
            else:
                result = subagent.invoke(state, config=subagent_config)

            # Emit subagent_end event
            final_message = _get_final_message_text(result)
            emit_event(
                "subagent_end",
                {
                    "name": subagent_type,
                    "result": final_message,
                },
            )

            if not runtime.tool_call_id:
                raise ValueError("Tool call ID is required for subagent invocation")

            return _create_command_from_result(result, runtime.tool_call_id)

        async def atask(
            description: str,
            subagent_type: str,
            runtime: ToolRuntime,
        ) -> str | Command:
            """Invoke a subagent asynchronously."""
            # Get compiled subagent
            subagent = compiled.get(subagent_type)
            if subagent is None:
                available = list(compiled.keys())
                return f"Unknown subagent type '{subagent_type}'. Available: {', '.join(available)}"

            # Emit subagent_start event
            emit_event(
                "subagent_start",
                {
                    "name": subagent_type,
                    "description": description,
                },
            )

            state = _prepare_subagent_state(description, runtime)

            # Execute subagent
            subagent_config = {"recursion_limit": recursion_limit}
            if stream_events and output_handlers:
                result = await _astream_subagent_with_events(
                    subagent, state, subagent_type
                )
            else:
                result = await subagent.ainvoke(state, config=subagent_config)

            # Emit subagent_end event
            final_message = _get_final_message_text(result)
            emit_event(
                "subagent_end",
                {
                    "name": subagent_type,
                    "result": final_message,
                },
            )

            if not runtime.tool_call_id:
                raise ValueError("Tool call ID is required for subagent invocation")

            return _create_command_from_result(result, runtime.tool_call_id)

        return StructuredTool.from_function(
            name="task",
            func=task,
            coroutine=atask,
            description=description,
        )

    def wrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], ModelResponse],
    ) -> ModelResponse:
        """Inject system prompt (no request storage needed)."""
        if self._system_prompt is not None:
            current_prompt = request.system_prompt or ""
            new_prompt = (
                f"{current_prompt}\n\n{self._system_prompt}"
                if current_prompt
                else self._system_prompt
            )
            return handler(request.override(system_prompt=new_prompt))
        return handler(request)

    async def awrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], Awaitable[ModelResponse]],
    ) -> ModelResponse:
        """Inject system prompt (no request storage needed, async)."""
        if self._system_prompt is not None:
            current_prompt = request.system_prompt or ""
            new_prompt = (
                f"{current_prompt}\n\n{self._system_prompt}"
                if current_prompt
                else self._system_prompt
            )
            return await handler(request.override(system_prompt=new_prompt))
        return await handler(request)
