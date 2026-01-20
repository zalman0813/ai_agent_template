"""Custom SubAgent Middleware implementation.

This middleware provides subagent capabilities without using create_deep_agent.
It follows LangChain v1.0 middleware patterns.
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


class SubAgentSpec(TypedDict):
    """Specification for a subagent."""

    name: str
    """The name of the subagent."""

    description: str
    """Description shown to main agent for deciding when to use this subagent."""

    system_prompt: str
    """The system prompt for the subagent."""

    tools: Sequence[BaseTool | Callable | dict[str, Any]]
    """Tools available to this subagent."""

    model: NotRequired[str | BaseChatModel]
    """Optional model override for this subagent."""

    middleware: NotRequired[list[AgentMiddleware]]
    """Optional additional middleware for this subagent."""


class CompiledSubAgent(TypedDict):
    """A pre-compiled subagent."""

    name: str
    """The name of the subagent."""

    description: str
    """Description of the subagent."""

    runnable: Runnable
    """The compiled runnable for the subagent."""


# State keys to exclude when passing state to subagents
_EXCLUDED_STATE_KEYS = {"messages", "todos", "structured_response"}

# Default system prompt explaining task tool usage (based on official LangChain version)
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


def _build_subagents(
    *,
    default_model: str | BaseChatModel,
    default_tools: Sequence[BaseTool | Callable | dict[str, Any]],
    default_middleware: list[AgentMiddleware] | None,
    subagents: list[SubAgentSpec | CompiledSubAgent],
    include_general_purpose: bool,
) -> tuple[dict[str, Runnable], list[str]]:
    """Build subagent instances from specifications.

    Args:
        default_model: Default model for subagents without model override.
        default_tools: Default tools for the general-purpose subagent.
        default_middleware: Middleware to apply to all subagents.
        subagents: List of subagent specs or pre-compiled agents.
        include_general_purpose: Whether to include a general-purpose subagent.

    Returns:
        Tuple of (agents_dict, description_list).
    """
    middleware_list = default_middleware or []
    agents: dict[str, Runnable] = {}
    descriptions: list[str] = []

    # Create general-purpose subagent if enabled
    if include_general_purpose:
        general_agent = create_agent(
            default_model,
            system_prompt="""You are a helpful assistant with access to various tools and skills.

When you receive a task, check if there are relevant skills available:
1. Look for skills in the context that match the task
2. Read the skill documentation using read_file() to understand how to use it
3. If the skill provides scripts, execute them using the execute() tool
4. Follow the skill's instructions exactly as documented

Important: Some operations (like cryptographic hashing) REQUIRE script execution - you cannot perform them directly. Always check for and use available skill scripts.""",
            tools=default_tools,
            middleware=list(middleware_list),
        )
        agents["general-purpose"] = general_agent
        descriptions.append(
            "- general-purpose: General-purpose agent for research and multi-step tasks"
        )

    # Process custom subagents
    for spec in subagents:
        descriptions.append(f"- {spec['name']}: {spec['description']}")

        # Check if it's a pre-compiled agent
        if "runnable" in spec:
            compiled = spec  # type: CompiledSubAgent
            agents[compiled["name"]] = compiled["runnable"]
            continue

        # Build from spec
        agent_spec = spec  # type: SubAgentSpec
        _tools = agent_spec.get("tools", list(default_tools))
        _model = agent_spec.get("model", default_model)
        _middleware = [
            *middleware_list,
            *agent_spec.get("middleware", []),
        ]

        agents[agent_spec["name"]] = create_agent(
            _model,
            system_prompt=agent_spec["system_prompt"],
            tools=_tools,
            middleware=_middleware,
        )

    return agents, descriptions


def _create_task_tool(
    *,
    default_model: str | BaseChatModel,
    default_tools: Sequence[BaseTool | Callable | dict[str, Any]],
    default_middleware: list[AgentMiddleware] | None,
    subagents: list[SubAgentSpec | CompiledSubAgent],
    include_general_purpose: bool,
    custom_description: str | None = None,
    stream_subagent_events: bool = False,
    output_handlers: list["OutputHandler"] | None = None,
) -> BaseTool:
    """Create the task tool for invoking subagents.

    Args:
        default_model: Default model for subagents.
        default_tools: Default tools for subagents.
        default_middleware: Middleware to apply to all subagents.
        subagents: List of subagent specifications.
        include_general_purpose: Whether to include general-purpose agent.
        custom_description: Optional custom tool description.
        stream_subagent_events: Whether to emit subagent_start/end events.
        output_handlers: Output handlers to receive subagent events.

    Returns:
        A StructuredTool that can invoke subagents.
    """
    # Helper to emit events to all output handlers
    def _emit_event(event_type: str, data: dict[str, Any]) -> None:
        if not stream_subagent_events or not output_handlers:
            return
        for handler in output_handlers:
            try:
                handler.emit(event_type, data)
            except Exception:
                pass  # Silently ignore handler errors
    agent_graphs, agent_descriptions = _build_subagents(
        default_model=default_model,
        default_tools=default_tools,
        default_middleware=default_middleware,
        subagents=subagents,
        include_general_purpose=include_general_purpose,
    )
    description_str = "\n".join(agent_descriptions)

    # Build tool description
    if custom_description is None:
        tool_description = TASK_TOOL_DESCRIPTION.format(
            available_agents=description_str
        )
    elif "{available_agents}" in custom_description:
        tool_description = custom_description.format(
            available_agents=description_str
        )
    else:
        tool_description = custom_description

    def _prepare_subagent_state(
        subagent_type: str,
        description: str,
        runtime: ToolRuntime,
    ) -> tuple[Runnable, dict]:
        """Prepare state for subagent invocation."""
        subagent = agent_graphs[subagent_type]

        # Create new state excluding messages/todos
        subagent_state = {
            k: v
            for k, v in runtime.state.items()
            if k not in _EXCLUDED_STATE_KEYS
        }
        subagent_state["messages"] = [HumanMessage(content=description)]

        return subagent, subagent_state

    def _stream_subagent_with_events(
        subagent: Runnable,
        state: dict,
        subagent_name: str,
    ) -> dict:
        """Stream subagent execution and emit tool events."""
        from langchain_core.messages import AIMessage as AIMsg
        from langchain_core.messages import ToolMessage as ToolMsg

        final_state = None
        for chunk in subagent.stream(state, stream_mode=["updates", "messages"]):
            if isinstance(chunk, tuple):
                mode, data = chunk
                if mode == "updates" and isinstance(data, dict):
                    for node_name, node_output in data.items():
                        if isinstance(node_output, dict) and "messages" in node_output:
                            messages = node_output["messages"]
                            if not isinstance(messages, list):
                                messages = [messages]
                            for msg in messages:
                                if isinstance(msg, AIMsg) and msg.tool_calls:
                                    for tool_call in msg.tool_calls:
                                        _emit_event("subagent_tool_call", {
                                            "subagent_name": subagent_name,
                                            "tool": tool_call.get("name"),
                                            "args": tool_call.get("args", {}),
                                            "id": tool_call.get("id"),
                                        })
                                elif isinstance(msg, ToolMsg):
                                    _emit_event("subagent_tool_result", {
                                        "subagent_name": subagent_name,
                                        "tool": msg.name,
                                        "result": msg.content[:500] if msg.content else "",
                                        "tool_call_id": msg.tool_call_id,
                                    })
                        final_state = node_output
        return final_state or {}

    async def _astream_subagent_with_events(
        subagent: Runnable,
        state: dict,
        subagent_name: str,
        max_retries: int = 1,
    ) -> dict:
        """Async stream subagent execution with retry logic.

        Args:
            subagent: The subagent runnable to execute.
            state: Input state for the subagent.
            subagent_name: Name of the subagent for event emission.
            max_retries: Maximum retry attempts (default 1 for subagents).

        Returns:
            Final state dict, or error message on failure.
        """
        from langchain_core.messages import AIMessage as AIMsg
        from langchain_core.messages import ToolMessage as ToolMsg

        from src.errors import classify_error

        for attempt in range(max_retries + 1):
            try:
                final_state = None
                chunk_count = 0

                async for chunk in subagent.astream(
                    state, stream_mode=["updates", "messages"]
                ):
                    chunk_count += 1
                    if isinstance(chunk, tuple):
                        mode, data = chunk
                        if mode == "updates" and isinstance(data, dict):
                            for node_name, node_output in data.items():
                                if (
                                    isinstance(node_output, dict)
                                    and "messages" in node_output
                                ):
                                    messages = node_output["messages"]
                                    if not isinstance(messages, list):
                                        messages = [messages]
                                    for msg in messages:
                                        if isinstance(msg, AIMsg) and msg.tool_calls:
                                            for tool_call in msg.tool_calls:
                                                _emit_event(
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
                                            _emit_event(
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
                                final_state = node_output

                # Handle empty stream
                if chunk_count == 0:
                    raise RuntimeError("No generations found in stream")

                return final_state or {}

            except Exception as e:
                llm_error = classify_error(e)

                # Emit subagent error event
                _emit_event(
                    "subagent_error",
                    {
                        "subagent_name": subagent_name,
                        "message": llm_error.message,
                        "attempt": attempt + 1,
                        "retryable": llm_error.retryable,
                    },
                )

                if not llm_error.retryable or attempt >= max_retries:
                    # Return error message gracefully instead of crashing
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

    def _create_command_from_result(
        result: dict,
        tool_call_id: str,
    ) -> Command:
        """Create Command with state update from subagent result."""
        state_update = {
            k: v for k, v in result.items() if k not in _EXCLUDED_STATE_KEYS
        }
        return Command(
            update={
                **state_update,
                "messages": [
                    ToolMessage(
                        result["messages"][-1].text,
                        tool_call_id=tool_call_id,
                    )
                ],
            }
        )

    def task(
        description: str,
        subagent_type: str,
        runtime: ToolRuntime,
    ) -> str | Command:
        """Invoke a subagent synchronously."""
        if subagent_type not in agent_graphs:
            allowed = ", ".join([f"`{k}`" for k in agent_graphs])
            return f"Unknown subagent type '{subagent_type}'. Available: {allowed}"

        # Emit subagent_start event
        _emit_event("subagent_start", {
            "name": subagent_type,
            "description": description,
        })

        subagent, state = _prepare_subagent_state(
            subagent_type, description, runtime
        )

        # Use streaming to emit internal tool events
        if stream_subagent_events and output_handlers:
            result = _stream_subagent_with_events(subagent, state, subagent_type)
        else:
            result = subagent.invoke(state)

        # Emit subagent_end event with full result for structured rendering
        final_message = result["messages"][-1].text if result.get("messages") else ""
        _emit_event("subagent_end", {
            "name": subagent_type,
            "result": final_message,  # Full result for frontend rendering
        })

        if not runtime.tool_call_id:
            raise ValueError("Tool call ID is required for subagent invocation")

        return _create_command_from_result(result, runtime.tool_call_id)

    async def atask(
        description: str,
        subagent_type: str,
        runtime: ToolRuntime,
    ) -> str | Command:
        """Invoke a subagent asynchronously."""
        if subagent_type not in agent_graphs:
            allowed = ", ".join([f"`{k}`" for k in agent_graphs])
            return f"Unknown subagent type '{subagent_type}'. Available: {allowed}"

        # Emit subagent_start event
        _emit_event("subagent_start", {
            "name": subagent_type,
            "description": description,
        })

        subagent, state = _prepare_subagent_state(
            subagent_type, description, runtime
        )

        # Use streaming to emit internal tool events
        if stream_subagent_events and output_handlers:
            result = await _astream_subagent_with_events(subagent, state, subagent_type)
        else:
            result = await subagent.ainvoke(state)

        # Emit subagent_end event with full result for structured rendering
        final_message = result["messages"][-1].text if result.get("messages") else ""
        _emit_event("subagent_end", {
            "name": subagent_type,
            "result": final_message,  # Full result for frontend rendering
        })

        if not runtime.tool_call_id:
            raise ValueError("Tool call ID is required for subagent invocation")

        return _create_command_from_result(result, runtime.tool_call_id)

    return StructuredTool.from_function(
        name="task",
        func=task,
        coroutine=atask,
        description=tool_description,
    )


class CustomSubAgentMiddleware(AgentMiddleware):
    """Middleware that provides subagent capabilities via a `task` tool.

    This middleware adds a task tool that can invoke specialized subagents.
    Subagents are useful for:
    - Complex multi-step tasks requiring isolated context
    - Domain-specific tasks needing specialized tools
    - Parallel task execution

    Example:
        ```python
        from langchain.agents import create_agent
        from src.middleware.subagent_middleware import (
            CustomSubAgentMiddleware,
            SubAgentSpec,
        )

        # Define a specialized subagent
        search_agent: SubAgentSpec = {
            "name": "web_search",
            "description": "Search the web for current information",
            "system_prompt": "You are a web research specialist.",
            "tools": [search_tool],
        }

        # Create middleware
        subagent_middleware = CustomSubAgentMiddleware(
            default_model=model,
            default_tools=[],
            subagents=[search_agent],
        )

        # Use with create_agent
        agent = create_agent(
            model,
            tools=[my_tool],
            middleware=[subagent_middleware],
        )
        ```
    """

    def __init__(
        self,
        *,
        default_model: str | BaseChatModel,
        default_tools: Sequence[BaseTool | Callable | dict[str, Any]] | None = None,
        default_middleware: list[AgentMiddleware] | None = None,
        subagents: list[SubAgentSpec | CompiledSubAgent] | None = None,
        system_prompt: str | None = TASK_SYSTEM_PROMPT,
        include_general_purpose: bool = True,
        task_description: str | None = None,
        stream_subagent_events: bool = False,
        output_handlers: list["OutputHandler"] | None = None,
    ) -> None:
        """Initialize the SubAgent Middleware.

        Args:
            default_model: Model to use for subagents (model instance or string).
            default_tools: Default tools for the general-purpose subagent.
            default_middleware: Middleware to apply to all subagents.
            subagents: List of subagent specifications.
            system_prompt: System prompt addition explaining task tool usage.
                Set to None to disable prompt injection.
            include_general_purpose: Whether to include a general-purpose subagent.
            task_description: Custom description for the task tool.
            stream_subagent_events: Whether to emit subagent_start/end events.
                When True, requires output_handlers to be set.
            output_handlers: Output handlers to receive subagent events.
                Required when stream_subagent_events is True.
        """
        super().__init__()
        self.system_prompt = system_prompt
        self.stream_subagent_events = stream_subagent_events
        self.output_handlers = output_handlers

        # Create the task tool
        task_tool = _create_task_tool(
            default_model=default_model,
            default_tools=default_tools or [],
            default_middleware=default_middleware,
            subagents=subagents or [],
            include_general_purpose=include_general_purpose,
            custom_description=task_description,
            stream_subagent_events=stream_subagent_events,
            output_handlers=output_handlers,
        )
        self.tools = [task_tool]

    def wrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], ModelResponse],
    ) -> ModelResponse:
        """Inject system prompt with subagent instructions."""
        if self.system_prompt is not None:
            current_prompt = request.system_prompt or ""
            new_prompt = (
                f"{current_prompt}\n\n{self.system_prompt}"
                if current_prompt
                else self.system_prompt
            )
            return handler(request.override(system_prompt=new_prompt))
        return handler(request)

    async def awrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], Awaitable[ModelResponse]],
    ) -> ModelResponse:
        """Inject system prompt with subagent instructions (async)."""
        if self.system_prompt is not None:
            current_prompt = request.system_prompt or ""
            new_prompt = (
                f"{current_prompt}\n\n{self.system_prompt}"
                if current_prompt
                else self.system_prompt
            )
            return await handler(request.override(system_prompt=new_prompt))
        return await handler(request)
