# LangChain Deep Agents SkillsMiddleware

> Official documentation for LangChain's SkillsMiddleware - middleware for loading and exposing agent skills to the system prompt.

**Sources:**
- https://reference.langchain.com/python/deepagents/middleware/skills/
- https://docs.langchain.com/oss/python/deepagents/middleware
- https://github.com/langchain-ai/deepagents

---

## Overview

`SkillsMiddleware` is part of the LangChain Deep Agents framework, introduced in November 2025. It provides middleware for loading and exposing agent skills to the system prompt using progressive disclosure (metadata first, full content on demand).

**Package:** `deepagents.middleware.skills.SkillsMiddleware`

**Key Features:**
- Discovers and loads skills from `SKILL.md` files
- Uses progressive disclosure for efficient context management
- Injects skill documentation into system prompts
- Supports multiple skill sources with override ordering

---

## Basic Usage

```python
from deepagents.backends.filesystem import FilesystemBackend
from deepagents.middleware.skills import SkillsMiddleware

backend = FilesystemBackend(root_dir="/path/to/skills")
middleware = SkillsMiddleware(
    backend=backend,
    sources=[
        "/path/to/skills/user/",
        "/path/to/skills/project/",
    ],
)
```

Skills are loaded in source order with later sources overriding earlier ones if they contain skills with the same name (last one wins).

---

## Constructor Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `backend` | `BACKEND_TYPES` | Backend instance for file operations. Use a factory for StateBackend: `lambda rt: StateBackend(rt)` |
| `sources` | `list[str]` | List of skill source paths (e.g., `["/skills/user/", "/skills/project/"]`). Source names are derived from the last path component. |

---

## Core Methods

### `modify_request`

Inject skills documentation into a model request's system message.

```python
def modify_request(request: ModelRequest) -> ModelRequest
```

**Parameters:**
- `request`: Model request to modify

**Returns:** New model request with skills documentation injected into system message

---

### `before_agent` / `abefore_agent`

Load skills metadata before agent execution.

```python
def before_agent(
    state: SkillsState,
    runtime: Runtime,
    config: RunnableConfig
) -> SkillsStateUpdate | None

async def abefore_agent(
    state: SkillsState,
    runtime: Runtime,
    config: RunnableConfig
) -> SkillsStateUpdate | None
```

Runs before each agent interaction to discover available skills from all configured sources. Re-loads on every call to capture any changes.

**Returns:** State update with `skills_metadata` populated, or `None` if already present

---

### `wrap_model_call` / `awrap_model_call`

Inject skills documentation into the system prompt.

```python
def wrap_model_call(
    request: ModelRequest,
    handler: Callable[[ModelRequest], ModelResponse]
) -> ModelResponse

async def awrap_model_call(
    request: ModelRequest,
    handler: Callable[[ModelRequest], Awaitable[ModelResponse]]
) -> ModelResponse
```

**Parameters:**
- `request`: Model request being processed
- `handler`: Handler function to call with modified request

**Returns:** Model response from handler

---

## Tool Call Wrapping

### `wrap_tool_call` / `awrap_tool_call`

Intercept tool execution for retries, monitoring, or modification.

```python
def wrap_tool_call(
    request: ToolCallRequest,
    handler: Callable[[ToolCallRequest], ToolMessage | Command[Any]],
) -> ToolMessage | Command[Any]
```

Multiple middleware compose automatically (first defined = outermost).

#### Example: Modify Request Before Execution

```python
def wrap_tool_call(self, request, handler):
    modified_call = {
        **request.tool_call,
        "args": {
            **request.tool_call["args"],
            "value": request.tool_call["args"]["value"] * 2,
        },
    }
    request = request.override(tool_call=modified_call)
    return handler(request)
```

#### Example: Retry on Error

```python
def wrap_tool_call(self, request, handler):
    for attempt in range(3):
        try:
            result = handler(request)
            if is_valid(result):
                return result
        except Exception:
            if attempt == 2:
                raise
    return result
```

#### Example: Conditional Retry Based on Response

```python
def wrap_tool_call(self, request, handler):
    for attempt in range(3):
        result = handler(request)
        if isinstance(result, ToolMessage) and result.status != "error":
            return result
        if attempt < 2:
            continue
        return result
```

#### Async Example: Caching

```python
async def awrap_tool_call(self, request, handler):
    if cached := await get_cache_async(request):
        return ToolMessage(content=cached, tool_call_id=request.tool_call["id"])
    result = await handler(request)
    await save_cache_async(request, result)
    return result
```

---

## All Methods Summary

| Method | Description |
|--------|-------------|
| `__init__` | Initialize the skills middleware |
| `modify_request` | Inject skills documentation into a model request's system message |
| `before_agent` | Load skills metadata before agent execution (synchronous) |
| `abefore_agent` | Load skills metadata before agent execution (async) |
| `wrap_model_call` | Inject skills documentation into the system prompt |
| `awrap_model_call` | Inject skills documentation into the system prompt (async) |
| `before_model` | Logic to run before the model is called |
| `abefore_model` | Async logic to run before the model is called |
| `after_model` | Logic to run after the model is called |
| `aafter_model` | Async logic to run after the model is called |
| `after_agent` | Logic to run after the agent execution completes |
| `aafter_agent` | Async logic to run after the agent execution completes |
| `wrap_tool_call` | Intercept tool execution for retries, monitoring, or modification |
| `awrap_tool_call` | Intercept and control async tool execution via handler callback |

---

## Properties

### `state_schema`

```python
state_schema = SkillsState
```

The schema for state passed to the middleware nodes.

### `tools`

```python
tools: Sequence[BaseTool]
```

Additional tools registered by the middleware.

### `name`

```python
name: str
```

The name of the middleware instance. Defaults to the class name, but can be overridden for custom naming.

---

## Key Concepts

- **SkillsMiddleware**: Middleware for loading and exposing agent skills to the system prompt
- **Progressive disclosure**: Only YAML frontmatter loads by default; full SKILL.md read on demand
- **Source ordering**: Skills are loaded in source order with later sources overriding earlier ones
- **Skill discovery**: Re-loads on every call to capture any changes to skills

---

## Reference Links

### Official Documentation
- https://docs.langchain.com/oss/python/deepagents/middleware
- https://reference.langchain.com/python/deepagents/middleware/skills/

### GitHub
- https://github.com/langchain-ai/deepagents
- https://github.com/langchain-ai/deepagents-quickstarts

### Related Deep Agents Documentation
- https://docs.langchain.com/oss/python/deepagents/overview
- https://docs.langchain.com/oss/python/deepagents/quickstart
- https://blog.langchain.com/deep-agents/
