# Agent Strands SDK

> Based on source code analysis of aws-samples/sample-strands-agent-with-agentcore
> and official Strands documentation (2025).

**Sources:**
- https://github.com/strands-agents/sdk-python
- https://strandsagents.com/latest/documentation/docs/user-guide/concepts/agents/hooks/
- https://strandsagents.com/latest/documentation/docs/api-reference/python/hooks/events/
- https://strandsagents.com/latest/documentation/docs/user-guide/concepts/agents/session-management/
- https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/code-interpreter-using-strands.html
- https://github.com/aws-samples/sample-strands-agent-with-agentcore

---

## Overview

Strands Agents is an open-source AI Agent SDK from Amazon (May 2025). It follows a
**model-driven** philosophy: the LLM acts as the orchestrator, deciding when to call tools
and how to reason — the developer provides tools, system prompt, and hooks.

**Three Core Components:**
1. **Language Model** — reasoning engine (Bedrock, Anthropic, OpenAI, etc.)
2. **System Prompt** — behavior definition
3. **Tools** — callable capabilities (`@tool` decorated functions)

---

## Agent Loop

```
User Input
    │
    ▼
[BeforeInvocationEvent] ◄── HookProvider can modify messages
    │
    ▼
Model Reasoning
    │
    ├─[BeforeModelCallEvent]  ◄── hook (read-only)
    ▼
LLM Inference
    │
    ├─[AfterModelCallEvent]   ◄── hook (can set retry=True)
    ▼
Tool Call? ──No──► Final Response
    │                    │
    Yes         [AfterInvocationEvent] ◄── hook (LIFO order)
    │
    ├─[BeforeToolCallEvent]  ◄── hook (can cancel_tool / modify tool_use)
    ▼
Tool Execution
    │
    ├─[AfterToolCallEvent]   ◄── hook (can modify result / set retry=True)
    ▼
Append to Conversation History
    │
    └──────────────────────────► loop back to Model Reasoning
```

**LIFO Order**: After-events execute in reverse registration order (like a stack/context manager).
This ensures cleanup symmetry with setup.

---

## Hooks System

### All Available Hook Events

| Event | Trigger | Mutable Fields |
|-------|---------|----------------|
| `AgentInitializedEvent` | Agent constructed | — (read-only) |
| `BeforeInvocationEvent` | Before each user request | `messages` |
| `AfterInvocationEvent` | After request completes (LIFO) | — |
| `MessageAddedEvent` | Message added to history | — |
| `BeforeModelCallEvent` | Before LLM call | — |
| `AfterModelCallEvent` | After LLM response (LIFO) | `retry: bool` |
| `BeforeToolCallEvent` | Before tool execution | `cancel_tool`, `selected_tool`, `tool_use` |
| `AfterToolCallEvent` | After tool execution (LIFO) | `result`, `retry: bool` |
| `MultiAgentInitializedEvent` | Multi-agent orchestrator init | — |
| `BeforeNodeCallEvent` | Before node in multi-agent graph | `cancel_node: bool \| str` |
| `AfterNodeCallEvent` | After node (LIFO) | — |

### HookProvider Pattern (Recommended)

```python
from strands import Agent
from strands.hooks import (
    HookProvider, HookRegistry,
    AgentInitializedEvent,
    BeforeInvocationEvent,
    AfterInvocationEvent,
    BeforeToolCallEvent,
    AfterToolCallEvent,
    BeforeModelCallEvent,
    AfterModelCallEvent,
)

class MyHookProvider(HookProvider):

    def register_hooks(self, registry: HookRegistry) -> None:
        # Register all desired events here
        registry.add_callback(AgentInitializedEvent, self.on_init)
        registry.add_callback(BeforeInvocationEvent, self.on_before_request)
        registry.add_callback(AfterToolCallEvent, self.on_after_tool)

    def on_init(self, event: AgentInitializedEvent) -> None:
        # Runs ONCE when agent is constructed
        # Use for: loading state, warming cache, initial setup
        print(f"Agent ready: {event.agent.name}")

    def on_before_request(self, event: BeforeInvocationEvent) -> None:
        # Runs before EVERY user request
        # event.messages: can prepend/inject context
        # event.invocation_state: request-level metadata
        user_id = event.invocation_state.get("user_id")
        print(f"Request from user: {user_id}")

    def on_after_tool(self, event: AfterToolCallEvent) -> None:
        # Runs after every tool call
        if event.exception:
            event.retry = True   # trigger auto-retry
        tool_name = event.tool_use.get("name")
        print(f"Tool {tool_name} completed")

# Register at agent construction
agent = Agent(
    tools=[my_tool],
    hooks=[MyHookProvider()],
)
```

### Direct Callback (Simple Cases)

```python
from strands.hooks import BeforeInvocationEvent

def log_request(event: BeforeInvocationEvent) -> None:
    print(f"Request: {event.invocation_state}")

agent.hooks.add_callback(BeforeInvocationEvent, log_request)
```

---

## State Management

Strands has two distinct state scopes:

### `agent.state` — Agent-Scope (Persistent Across Turns)

```python
# Set during hooks or tools
event.agent.state.set("skills_metadata", [...])
event.agent.state.set("user_preferences", {"lang": "zh"})

# Read anywhere
meta = event.agent.state.get("skills_metadata")  # None if not set

# Delete
event.agent.state.delete("temp_key")
```

- Persists across all turns of the same agent instance
- Survives across invocations (within the same process)
- If using `S3SessionManager`, serialized to S3 and restored on next construction

### `invocation_state` — Request-Scope (Per-Turn)

```python
# Pass at call time
result = agent(
    "Analyze the market data",
    invocation_state={
        "user_id": "user-123",
        "session_id": "sess-456",
        "db_client": db_connection,   # can pass Python objects
    }
)

# Access in hooks
def on_before(event: BeforeInvocationEvent) -> None:
    user_id = event.invocation_state.get("user_id")

# Access in tools
from strands import tool, ToolContext

@tool(context=True)
def my_tool(query: str, tool_context: ToolContext = None) -> str:
    user_id = tool_context.invocation_state.get("user_id")
    session_id = tool_context.invocation_state.get("session_id")
    return f"Running for {user_id}/{session_id}"
```

---

## Tool Registration

### Three Patterns

```python
from strands import tool, Agent, ToolContext

# Pattern 1: Simple @tool decorator
@tool
def get_weather(city: str) -> str:
    """Get weather for a city.

    Args:
        city: The city name.

    Returns:
        Weather description.
    """
    return f"Sunny in {city}"

# Pattern 2: @tool with ToolContext for state access
@tool(context=True)
def read_user_data(key: str, tool_context: ToolContext = None) -> str:
    """Read from user-scoped storage.

    Args:
        key: Storage key to read.
    """
    user_id = tool_context.invocation_state.get("user_id", "default")
    data = tool_context.agent.state.get(f"data_{user_id}_{key}")
    return str(data)

# Pattern 3: Async tool (executes concurrently with other async tools)
@tool
async def fetch_url(url: str) -> str:
    """Fetch content from URL.

    Args:
        url: URL to fetch.
    """
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            return await resp.text()

# Register with agent
agent = Agent(
    model="us.anthropic.claude-sonnet-4-6-v1",
    tools=[get_weather, read_user_data, fetch_url],
    system_prompt="You are a helpful assistant.",
)
```

### How Tools Reach the Model

```
Agent(tools=[tool_a, tool_b, tool_c])
    │
    └── framework calls model.bind_tools([tool_a, tool_b, tool_c])
            └── tool schemas injected into every model request payload

LLM response contains tool_call:
    { "name": "get_weather", "input": { "city": "Tokyo" } }
    │
    └── Strands dispatches by name to matching @tool function
            └── returns ToolResult → appended to conversation history
```

---

## System Prompt Injection

### Static (at construction)

```python
agent = Agent(
    system_prompt="You are a data analyst. Always respond in Traditional Chinese.",
    tools=[...],
)
```

### Dynamic (via BeforeInvocationEvent hook)

```python
class DynamicPromptHook(HookProvider):

    def register_hooks(self, registry: HookRegistry) -> None:
        registry.add_callback(BeforeInvocationEvent, self.inject)

    def inject(self, event: BeforeInvocationEvent) -> None:
        # Prepend context to first message this turn
        extra_context = self._build_context(event.invocation_state)
        if event.messages:
            # Inject into existing message
            first_content = event.messages[0]["content"]
            if isinstance(first_content, list):
                first_content.insert(0, {"text": extra_context})
            else:
                event.messages[0]["content"] = extra_context + "\n\n" + first_content

    def _build_context(self, state: dict) -> str:
        return f"[Context] user={state.get('user_id')} date={today}"
```

---

## S3 Session Manager

Persists agent state (conversation history + `agent.state`) to S3 across process restarts.

```python
import boto3
from strands import Agent
from strands.session.s3_session_manager import S3SessionManager

session_manager = S3SessionManager(
    session_id="user-123-session-456",   # unique per conversation
    bucket="my-agent-sessions",
    prefix="prod/agents/",               # optional S3 key prefix
    boto_session=boto3.Session(region_name="us-west-2"),
    region_name="us-west-2",
)

agent = Agent(
    system_prompt="You are a helpful assistant.",
    tools=[...],
    session_manager=session_manager,
)

# First run: state saved to S3 after each turn
agent("My name is Alice")

# Process restart, new agent instance, same session_id:
# → conversation history AND agent.state both restored from S3
agent("What is my name?")  # → "Your name is Alice"
```

**Required IAM Permissions:**
```json
{
  "Action": ["s3:PutObject", "s3:GetObject", "s3:DeleteObject", "s3:ListBucket"],
  "Resource": ["arn:aws:s3:::my-agent-sessions", "arn:aws:s3:::my-agent-sessions/*"]
}
```

---

## AgentCore Code Interpreter

AWS-managed sandboxed Python execution environment.

```python
from strands_tools.code_interpreter import AgentCoreCodeInterpreter
from strands_tools.code_interpreter.models import (
    ExecuteCodeAction, ExecuteCommandAction,
    WriteFilesAction, ReadFilesAction,
    ListFilesAction, RemoveFilesAction,
    FileContent, LanguageType,
)

# Session-cached interpreter (reuse per user/session)
interpreter = AgentCoreCodeInterpreter(region="us-west-2")

# Execute Python
result = interpreter.execute_code(ExecuteCodeAction(
    type="executeCode",
    session_name="user-123-sess-456",
    code="import pandas as pd\nprint(pd.Series([1,2,3]).mean())",
    language=LanguageType.PYTHON,
    clear_context=False,   # keep variables between calls
))

# Execute shell command
result = interpreter.execute_command(ExecuteCommandAction(
    type="executeCommand",
    session_name=session_name,
    command="pip install requests",
))

# Write files into sandbox
interpreter.write_files(WriteFilesAction(
    type="writeFiles",
    session_name=session_name,
    content=[FileContent(path="data.csv", text=csv_content)],
))

# Read files out of sandbox
result = interpreter.read_files(ReadFilesAction(
    type="readFiles",
    session_name=session_name,
    paths=["output.json", "chart.png"],  # binary returns as blob
))
```

**Session persistence:** Variables and files persist within the same `session_name`
across multiple tool calls. Use module-level dict to cache interpreter instances.

---

## LangChain vs Strands Comparison

| Concept | LangChain DeepAgents | Strands Agents |
|---------|---------------------|----------------|
| Design philosophy | Graph-driven (explicit nodes/edges) | Model-driven (LLM orchestrates) |
| Middleware / Hooks | `AgentMiddleware` class | `HookProvider` class |
| Before request | `before_agent()` | `AgentInitializedEvent` + `BeforeInvocationEvent` |
| System prompt injection | `wrap_model_call()` | `BeforeInvocationEvent` |
| After model | `after_model()` | `AfterModelCallEvent` |
| Tool intercept | `wrap_tool_call()` | `BeforeToolCallEvent` / `AfterToolCallEvent` |
| Agent state | `AgentState` TypedDict (LangGraph) | `agent.state` key-value store |
| State cache check | `if "key" in state` | `agent.state.get("key")` |
| Tool registration | `mw.tools` → `model.bind_tools()` | `Agent(tools=[...])` directly |
| Session persistence | LangGraph Checkpointer | `S3SessionManager` |
| Sandbox execution | `execute` shell tool | `AgentCoreCodeInterpreter` |
| AWS integration | Generic (requires extra config) | Native (Bedrock, S3, Lambda) |

---

## Reference Links

- https://strandsagents.com/latest/documentation/docs/user-guide/concepts/agents/hooks/
- https://strandsagents.com/latest/documentation/docs/api-reference/python/hooks/events/
- https://strandsagents.com/latest/documentation/docs/user-guide/concepts/agents/session-management/
- https://strandsagents.com/latest/documentation/docs/api-reference/python/session/s3_session_manager/
- https://strandsagents.com/latest/documentation/docs/user-guide/concepts/tools/custom-tools/
- https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/code-interpreter-using-strands.html
- https://github.com/strands-agents/sdk-python
- https://github.com/strands-agents/tools
- https://github.com/aws-samples/sample-strands-agent-with-agentcore
- https://aws.amazon.com/blogs/opensource/introducing-strands-agents-an-open-source-ai-agents-sdk/
