# SubAgent Middleware API Reference

This document explains the `CustomSubAgentMiddleware` that provides subagent capabilities using compile-time resolution pattern.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                   CustomSubAgentMiddleware                       │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  __init__(default_model, default_tools, ...)            │    │
│  │  - Compile subagents at initialization                   │    │
│  │  - Create task tool with compiled subagents              │    │
│  └─────────────────────────────────────────────────────────┘    │
│                              │                                   │
│                              ▼                                   │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  _compile_subagents() → dict[str, Runnable]             │    │
│  │  - Create general-purpose subagent                       │    │
│  │  - Create custom subagents from specs                    │    │
│  └─────────────────────────────────────────────────────────┘    │
│                              │                                   │
│                              ▼                                   │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  self.tools = [task_tool]                                │    │
│  │  - Injected into main agent at create_agent()            │    │
│  └─────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼ task tool invoked
┌─────────────────────────────────────────────────────────────────┐
│  task(description, subagent_type, runtime)                       │
│  - Lookup compiled subagent by type                              │
│  - Emit subagent_start event                                     │
│  - Execute subagent.invoke(state)                                │
│  - Emit subagent_end event                                       │
│  - Return Command with result                                    │
└─────────────────────────────────────────────────────────────────┘
```

**Key Insight**: Subagents are compiled at initialization time using explicit `default_model`, `default_tools`, and `default_middleware`. This eliminates runtime complexity and contextvars.

---

## API Reference

### CustomSubAgentMiddleware

```python
from src.middleware import CustomSubAgentMiddleware, SubAgentSpec

CustomSubAgentMiddleware(
    default_model: BaseChatModel,              # Required: Model for subagents
    default_tools: Sequence[...] | None = None,
    default_middleware: list[AgentMiddleware] | None = None,
    subagents: list[SubAgentSpec] | None = None,
    system_prompt: str | None = TASK_SYSTEM_PROMPT,
    include_general_purpose: bool = True,
    task_description: str | None = None,
    stream_subagent_events: bool = False,
    output_handlers: list[OutputHandler] | None = None,
    subagent_recursion_limit: int = 150,
)
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `default_model` | `BaseChatModel` | **Required** | Model for all subagents |
| `default_tools` | `Sequence[BaseTool]` | `None` | Default tools for subagents |
| `default_middleware` | `list[AgentMiddleware]` | `None` | Default middleware for subagents |
| `subagents` | `list[SubAgentSpec]` | `None` | Custom subagent specifications |
| `system_prompt` | `str \| None` | `TASK_SYSTEM_PROMPT` | System prompt explaining task tool usage. Set `None` to disable |
| `include_general_purpose` | `bool` | `True` | Include built-in general-purpose subagent |
| `task_description` | `str \| None` | `None` | Custom description for task tool |
| `stream_subagent_events` | `bool` | `False` | Emit subagent events to output handlers |
| `output_handlers` | `list[OutputHandler]` | `None` | Handlers to receive subagent events |
| `subagent_recursion_limit` | `int` | `150` | Max steps for subagent execution |

---

## SubAgentSpec

TypedDict for defining subagent specifications:

```python
class SubAgentSpec(TypedDict):
    name: str                                    # Required: Unique identifier
    description: str                             # Required: Shown to main agent

    # Optional Overrides (defaults from middleware)
    system_prompt: NotRequired[str]              # Default: GENERAL_PURPOSE_SYSTEM_PROMPT
    tools: NotRequired[Sequence[BaseTool]]       # Default: default_tools
    middleware: NotRequired[list[...]]           # Default: default_middleware
    model: NotRequired[BaseChatModel]            # Default: default_model

    # Pre-compiled
    runnable: NotRequired[Runnable]              # Pre-compiled agent (ignores other config)
```

### Override Priority

For each subagent:

| Field | Priority |
|-------|----------|
| `model` | `spec.model` → `default_model` |
| `tools` | `spec.tools` → `default_tools` |
| `middleware` | `spec.middleware` → `default_middleware` |
| `system_prompt` | `spec.system_prompt` → `GENERAL_PURPOSE_SYSTEM_PROMPT` |

---

## Usage Examples

### Example 1: Basic Setup

```python
from src.middleware import CustomSubAgentMiddleware

# Create middleware with explicit configuration
middleware = CustomSubAgentMiddleware(
    default_model=model,
    default_tools=[read_file, write_file, search_tool],
    default_middleware=[SummarizationMiddleware(model)],
    include_general_purpose=True,
)

agent = create_agent(
    model,
    tools=[search_tool],
    middleware=[middleware],
)
```

### Example 2: Multiple Custom Subagents

```python
middleware = CustomSubAgentMiddleware(
    default_model=model,
    default_tools=all_tools,
    default_middleware=base_middleware,
    subagents=[
        {
            "name": "researcher",
            "description": "Research agent for information gathering",
            "system_prompt": "You are a research specialist...",
        },
        {
            "name": "writer",
            "description": "Writing agent for content creation",
            "system_prompt": "You are a content writer...",
        },
    ],
)
```

### Example 3: Subagent with Custom Tools

```python
from langchain_tavily import TavilySearch

middleware = CustomSubAgentMiddleware(
    default_model=model,
    default_tools=file_tools,  # For general-purpose
    subagents=[
        {
            "name": "web_search",
            "description": "Search the web for information",
            "tools": [TavilySearch()],  # Custom tools for this subagent
            "system_prompt": "You are a web search specialist...",
        },
    ],
)
```

### Example 4: Streaming SubAgent Events

```python
from src.observation.outputs import ConsoleOutput

outputs = [ConsoleOutput(verbose=True)]

middleware = CustomSubAgentMiddleware(
    default_model=model,
    default_tools=tools,
    stream_subagent_events=True,
    output_handlers=outputs,
)

# Events emitted:
# - subagent_start: {"name": "...", "description": "..."}
# - subagent_tool_call: {"subagent_name": "...", "tool": "...", ...}
# - subagent_tool_result: {"subagent_name": "...", "tool": "...", ...}
# - subagent_end: {"name": "...", "result": "..."}
```

### Example 5: Real-World Configuration (skill-agent)

```python
# Create tool-providing middleware first
todo_middleware = TodoListMiddleware()
skills_middleware = SkillsMiddleware(backend=backend_factory, sources=["/skills/"])
filesystem_middleware = FilesystemMiddleware(backend=backend_factory)

# Collect tools for subagents
subagent_tools = [
    *todo_middleware.tools,
    *skills_middleware.tools,
    *filesystem_middleware.tools,
    search_tool,
]

# Define subagent middleware stack
subagent_middleware = [
    SummarizationMiddleware(model, max_tokens_before_summary=170000),
    AnthropicPromptCachingMiddleware(unsupported_model_behavior="ignore"),
    PatchToolCallsMiddleware(),
]

# Create CustomSubAgentMiddleware
CustomSubAgentMiddleware(
    default_model=model,
    default_tools=subagent_tools,
    default_middleware=subagent_middleware,
    include_general_purpose=True,
    stream_subagent_events=output_handlers is not None,
    output_handlers=output_handlers,
)
```

---

## Compile-Time Resolution Flow

```
┌─────────────────────────────────────────────────────────────────┐
│ 1. Middleware Initialization                                     │
│    CustomSubAgentMiddleware(default_model=m, default_tools=t)    │
│    - _compile_subagents() called immediately                     │
│    - All subagents created and cached                            │
│    - task tool created with closure to compiled agents           │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ 2. create_agent() Assembly                                       │
│    agent = create_agent(model, tools=[...], middleware=[...])    │
│    - middleware.tools (task tool) injected into agent            │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ 3. wrap_model_call() Invoked                                     │
│    - Inject system prompt (no request storage needed)            │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ 4. task() Tool Called                                            │
│    - subagent = compiled[subagent_type]  ← direct lookup         │
│    - emit subagent_start event                                   │
│    - subagent.invoke(state)                                      │
│    - emit subagent_end event                                     │
│    - return Command with result                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Built-in General-Purpose SubAgent

When `include_general_purpose=True` (default), a built-in subagent is available:

```python
{
    "name": "general-purpose",
    "description": "General-purpose agent for research and multi-step tasks",
    "system_prompt": GENERAL_PURPOSE_SYSTEM_PROMPT,
    "tools": default_tools,
    "middleware": default_middleware,
    "model": default_model,
}
```

This subagent:
- Uses all `default_tools`
- Uses all `default_middleware`
- Suitable for complex, multi-step tasks

---

## Best Practices

### 1. Collect Tools Before Creating Middleware

```python
# Good: Collect tools from other middleware first
todo_middleware = TodoListMiddleware()
filesystem_middleware = FilesystemMiddleware(backend=backend)

subagent_tools = [
    *todo_middleware.tools,
    *filesystem_middleware.tools,
]

CustomSubAgentMiddleware(
    default_model=model,
    default_tools=subagent_tools,
    ...
)
```

### 2. Use Shared Middleware for Subagents

```python
# Common middleware for all subagents
subagent_middleware = [
    SummarizationMiddleware(model, max_tokens=170000),
    PatchToolCallsMiddleware(),
]

CustomSubAgentMiddleware(
    default_model=model,
    default_middleware=subagent_middleware,
    ...
)
```

### 3. Stream Events for Visibility

```python
# Enable event streaming for debugging
CustomSubAgentMiddleware(
    default_model=model,
    default_tools=tools,
    stream_subagent_events=True,
    output_handlers=[ConsoleOutput()],
)
```

---

## File References

- `src/middleware/subagent_middleware.py` - Main implementation
- `src/middleware/__init__.py` - Public exports
- `examples/skill-agent/agent.py` - Usage example
