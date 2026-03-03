# LangChain Deep Agents SkillsMiddleware

> Documentation based on source code analysis of the DeepAgents framework (November 2025).
> Corrected from official docs where behavior differed from actual implementation.

**Sources:**
- https://github.com/langchain-ai/deepagents/blob/main/libs/deepagents/deepagents/middleware/skills.py
- https://github.com/langchain-ai/deepagents/blob/main/libs/deepagents/deepagents/middleware/filesystem.py
- https://github.com/langchain-ai/deepagents/blob/main/libs/deepagents/deepagents/graph.py
- https://reference.langchain.com/python/deepagents/middleware/skills/

---

## Overview

`SkillsMiddleware` is part of the LangChain Deep Agents framework. Its **sole responsibility** is
context engineering: injecting skill metadata into the system prompt using progressive disclosure.

**It does NOT register any tools.** Skill execution relies entirely on `FilesystemMiddleware`'s
`read_file` and `execute` tools.

**Package:** `deepagents.middleware.skills.SkillsMiddleware`

**Key Features:**
- Discovers and loads skills from `SKILL.md` files
- Uses progressive disclosure for efficient context management (metadata first, full content on demand)
- Injects skill documentation into system prompts
- Supports multiple skill sources with override ordering (last source wins)

---

## Architecture: Complete Flow

### 1. create_agent Tool Collection

```
create_agent(
    model=model,
    tools=[user_tool_a, ...],
    middleware=[
        TodoListMiddleware(),       # tools = [write_todos]
        FilesystemMiddleware(...),  # tools = [ls, read_file, write_file,
                                   #           edit_file, glob, grep, execute]
        SkillsMiddleware(...),      # tools = []  <-- EMPTY, only injects system prompt
        SummarizationMiddleware(),  # tools = []
    ]
)
        │
        ▼  framework collects tools from every middleware.tools
all_tools = user_tools + mw1.tools + mw2.tools + mw3.tools + ...
        │
        ▼
model_with_tools = model.bind_tools(all_tools)
        │                   └── puts tool schemas into every model request
        ▼
LangGraph ToolNode(tools=all_tools)
        └── dispatches by tool name when model emits a tool_call
```

### 2. Agent Lifetime: SkillsMiddleware + FilesystemMiddleware + Backend

```
AGENT START
    │
    ▼
┌─────────────────────────────────────────────────────────────────┐
│  before_agent()  [runs ONCE per session]                        │
│                                                                 │
│  if "skills_metadata" in state:                                 │
│      return None  ◄── already loaded, skip (0 IO)              │
│  else:                                                          │
│      ┌── FILESYSTEM IO (only this time) ──────────────────┐    │
│      │  backend.ls_info("/skills/user/")                  │    │
│      │  backend.ls_info("/skills/project/")               │    │
│      │  backend.download_files([...SKILL.md paths...])    │    │
│      │   → parse YAML frontmatter only (not full body)    │    │
│      └────────────────────────────────────────────────────┘    │
│                                                                 │
│  source ordering: later source overrides same-name skill        │
│  /skills/user/market-intel  ──► overridden by                  │
│  /skills/project/market-intel ◄── this one wins                │
│                                                                 │
│  return SkillsStateUpdate(skills_metadata=[...])                │
│         └── SET into state["skills_metadata"]  (not append)    │
└─────────────────────────────────────────────────────────────────┘
    │
    │  skills_metadata now cached in AgentState
    ▼
┌── AGENT LOOP ───────────────────────────────────────────────────┐
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  wrap_model_call()  [every model call, in-memory only]   │  │
│  │                                                          │  │
│  │  modify_request(request):                                │  │
│  │    read skills_metadata from state  ◄── 0 IO            │  │
│  │    format as text:                                       │  │
│  │      "## Available Skills                                │  │
│  │       - market-intel: Gather market intelligence         │  │
│  │       - web-search: Search the web                       │  │
│  │       To read full instructions:                         │  │
│  │       read_file('/skills/project/market-intel/SKILL.md')"│  │
│  │    inject into request.system_prompt                     │  │
│  │                                                          │  │
│  │  handler(modified_request)  ──► LLM                      │  │
│  └──────────────────────────────────────────────────────────┘  │
│                         │                                       │
│         LLM sees skill list, decides to use "market-intel"     │
│                         │                                       │
│                         ▼                                       │
│  ┌── STAGE 2: Full Skill Instructions ─────────────────────┐   │
│  │                                                         │   │
│  │  LLM emits tool_call:                                   │   │
│  │    { name: "read_file",                                 │   │
│  │      args: { file_path:                                 │   │
│  │        "/skills/project/market-intel/SKILL.md" } }      │   │
│  │                                                         │   │
│  │  LangGraph ToolNode dispatches to FilesystemMiddleware  │   │
│  │                                                         │   │
│  │  FilesystemMiddleware.read_file()                       │   │
│  │    └── backend.download_files(path)  ◄── IO here        │   │
│  │        └── returns full SKILL.md content                │   │
│  │                                                         │   │
│  │  LLM now has full instructions + script path            │   │
│  └─────────────────────────────────────────────────────────┘   │
│                         │                                       │
│                         ▼                                       │
│  ┌── STAGE 3: Skill Script Execution ──────────────────────┐   │
│  │                                                         │   │
│  │  LLM emits tool_call:                                   │   │
│  │    { name: "execute",                                   │   │
│  │      args: { command:                                   │   │
│  │        "python market_intel.py --query 'AI 2025'" } }   │   │
│  │                                                         │   │
│  │  FilesystemMiddleware.execute()                         │   │
│  │    └── backend.execute(command)  ◄── sandbox exec       │   │
│  │        └── returns stdout + exit code                   │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
    │
    ▼
after_agent()  [cleanup if needed]
```

### 3. State Architecture

```
AgentState  (LangGraph base TypedDict)
┌──────────────────────────────────────────┐
│  messages: Annotated[list, operator.add] │  ← append reducer
│  input: str                              │
│  output: str | None                      │
└──────────────────────────────────────────┘
            ▲  extends
            │
SkillsState  (declared by SkillsMiddleware.state_schema)
┌──────────────────────────────────────────┐
│  ... inherits AgentState fields          │
│                                          │
│  skills_metadata:                        │
│    NotRequired[                          │
│      Annotated[                          │
│        list[SkillMetadata],              │
│        PrivateStateAttr                  │  ← NOT propagated to subagents
│      ]                                   │
│    ]                                     │
└──────────────────────────────────────────┘

State update from before_agent():
  return SkillsStateUpdate(skills_metadata=[...])
         └── state["skills_metadata"] = [...]   ← SET, not append
             (key replace, same as dict merge)

PrivateStateAttr effect:
  MAIN AGENT state.skills_metadata = [skill_a, skill_b]
      │
      └── spawns SUBAGENT
              └── state.skills_metadata = ???
                  PrivateStateAttr → NOT inherited
                  subagent's SkillsMiddleware loads its own
```

### 4. IO Cost Summary

```
Event                          IO?        When
─────────────────────────────────────────────────────────
before_agent (1st call)        YES        once per session
before_agent (2nd+ call)       NO         state cache hit
wrap_model_call (every loop)   NO         in-memory read
read_file tool (on demand)     YES        when LLM requests
execute tool (on demand)       YES        when LLM runs skill
```

---

## State Schema

```python
class SkillsState(AgentState):
    """State for the skills middleware."""

    skills_metadata: NotRequired[Annotated[list[SkillMetadata], PrivateStateAttr]]
    # Not propagated to parent/child agents. Loaded once, cached for session lifetime.


class SkillsStateUpdate(TypedDict):
    """Returned by before_agent to SET skills_metadata in state."""

    skills_metadata: list[SkillMetadata]
```

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
        "/path/to/skills/project/",  # overrides user/ if same skill name
    ],
)
```

Skills are loaded in source order. Later sources override earlier ones for same-name skills (last wins).

---

## Constructor Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `backend` | `BACKEND_TYPES` | Backend instance for file operations. Use a factory for StateBackend: `lambda rt: StateBackend(rt)` |
| `sources` | `list[str]` | List of skill source paths. Source names derived from last path component. |

---

## Core Methods

### `before_agent` / `abefore_agent`

Load skills metadata before agent execution. **Runs only once per session** (state-cached).

```python
def before_agent(
    state: SkillsState,
    runtime: Runtime,
    config: RunnableConfig
) -> SkillsStateUpdate | None
```

Actual behavior (from source):
```python
# If already loaded, skip entirely (0 IO)
if "skills_metadata" in state:
    return None

# First call: scan filesystem, parse YAML frontmatter only
backend = self._get_backend(state, runtime, config)
all_skills: dict[str, SkillMetadata] = {}
for source_path in self.sources:
    source_skills = _list_skills(backend, source_path)
    for skill in source_skills:
        all_skills[skill["name"]] = skill  # last source wins

return SkillsStateUpdate(skills_metadata=list(all_skills.values()))
```

> **Note:** Official docs say "Re-loads on every call to capture any changes."
> This is incorrect. Actual source shows state-cache check first — skills are
> loaded only once. Dynamic SKILL.md changes are NOT picked up mid-session.

---

### `wrap_model_call` / `awrap_model_call`

Inject skills metadata into system prompt on every model call. Pure in-memory, no IO.

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

Internally calls `modify_request(request)` which reads `skills_metadata` from state
and appends a formatted skill list to `request.system_prompt`.

---

### `modify_request`

Stateless system prompt injection (called by `wrap_model_call`).

```python
def modify_request(request: ModelRequest) -> ModelRequest
```

Formats the injected block approximately as:
```
## Available Skills

### market-intel
Description: Gather market intelligence data
Trigger: When analyzing market trends or competitors

### web-search
Description: Search the web for current information
Trigger: When user asks about current events

Skills follow a progressive disclosure pattern - metadata shown above,
full instructions available by reading the SKILL.md file at the path shown.
```

---

## Properties

### `state_schema`

```python
state_schema = SkillsState
```

Tells `create_agent` to merge `SkillsState` fields into the graph's combined state TypedDict.

### `tools`

```python
tools: Sequence[BaseTool] = []  # effectively empty
```

**SkillsMiddleware registers NO tools.** Skill execution depends on `FilesystemMiddleware`
providing `read_file` (to fetch full SKILL.md) and `execute` (to run skill scripts).

### `name`

```python
name: str
```

Middleware instance name. Defaults to class name.

---

## All Methods Summary

| Method | Description |
|--------|-------------|
| `__init__` | Initialize with backend and source paths |
| `modify_request` | Inject skills metadata into system prompt (stateless, in-memory) |
| `before_agent` | Load skills from filesystem into state (once per session) |
| `abefore_agent` | Async version of `before_agent` |
| `wrap_model_call` | Call `modify_request` before passing request to model |
| `awrap_model_call` | Async version of `wrap_model_call` |
| `before_model` | Base hook (not overridden by SkillsMiddleware) |
| `after_model` | Base hook (not overridden by SkillsMiddleware) |
| `after_agent` | Base hook (not overridden by SkillsMiddleware) |
| `wrap_tool_call` | Base hook (not overridden by SkillsMiddleware) |

---

## Tool Registration: Who Provides What

When `create_deep_agent()` builds the middleware stack, `create_agent` collects `mw.tools`
from every middleware and calls `model.bind_tools(all_tools)`:

| Middleware | Tools Registered |
|------------|-----------------|
| `TodoListMiddleware` | `write_todos` |
| `FilesystemMiddleware` | `ls`, `read_file`, `write_file`, `edit_file`, `glob`, `grep`, `execute` |
| `SubAgentMiddleware` | `task` |
| `SkillsMiddleware` | *(none)* |
| `SummarizationMiddleware` | *(none)* |
| User-provided tools | whatever the user passes |

Skills are executed by the LLM calling `read_file` to fetch full SKILL.md instructions,
then `execute` to run the skill script — both from `FilesystemMiddleware`.

---

## Progressive Disclosure: Three Stages

| Stage | Trigger | IO | Content |
|-------|---------|-----|---------|
| **1. Metadata** | Every model call (system prompt) | 0 (in-memory) | Name + description from YAML frontmatter |
| **2. Full instructions** | LLM calls `read_file(SKILL.md)` | 1 backend read | Complete SKILL.md body with steps + script path |
| **3. Execution** | LLM calls `execute(script)` | 1 sandbox exec | Skill output returned as ToolMessage |

---

## Key Concepts

- **SkillsMiddleware**: Context engineering only — injects skill awareness into system prompt
- **Progressive disclosure**: YAML metadata → on-demand full SKILL.md → script execution
- **Lazy load once**: Skills scanned from filesystem once per session, then served from state
- **PrivateStateAttr**: `skills_metadata` is not propagated to subagents; each loads independently
- **Source ordering**: Later sources override earlier ones for same-name skills (last wins)
- **No own tools**: Skill execution is delegated to `FilesystemMiddleware`'s `read_file` + `execute`

---

## Reference Links

### Official Documentation
- https://docs.langchain.com/oss/python/deepagents/middleware
- https://reference.langchain.com/python/deepagents/middleware/skills/

### GitHub Source
- https://github.com/langchain-ai/deepagents
- https://github.com/langchain-ai/deepagents/blob/main/libs/deepagents/deepagents/middleware/skills.py
- https://github.com/langchain-ai/deepagents/blob/main/libs/deepagents/deepagents/middleware/filesystem.py

### Related Deep Agents Documentation
- https://docs.langchain.com/oss/python/deepagents/overview
- https://docs.langchain.com/oss/python/deepagents/quickstart
- https://blog.langchain.com/deep-agents/
