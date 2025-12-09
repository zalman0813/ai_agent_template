# Streaming Output API Reference

This document explains the streaming output system for agent observation, including event types, data structures, and frontend integration patterns.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        AgentObserver                             │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  agent.stream(stream_mode=["updates", "messages"])      │    │
│  └─────────────────────────────────────────────────────────┘    │
│                              │                                   │
│              ┌───────────────┴───────────────┐                  │
│              ▼                               ▼                  │
│     _handle_messages_chunk()       _handle_updates_chunk()      │
│              │                               │                  │
│              ▼                               ▼                  │
│         llm_token                 node_start/node_end           │
│                                   tool_call/tool_result         │
│                                   llm_end                       │
└──────────────────────────────────────────────────────────────────┘
                              │
                              ▼ emit(event_type, data)
┌─────────────────────────────────────────────────────────────────┐
│                      OutputHandler[]                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐   │
│  │ConsoleOutput │  │JsonFileOutput│  │CallbackOutput        │   │
│  │  (Terminal)  │  │   (.json)    │  │ (UI/WebSocket/SSE)   │   │
│  └──────────────┘  └──────────────┘  └──────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

---

## Event Types Reference

### Core Events (12 types)

| Event Type | Trigger | Data Schema |
|------------|---------|-------------|
| `llm_token` | LLM streaming output | `{"token": "text chunk"}` |
| `llm_start` | LLM begins thinking | `{}` (reserved, not emitted) |
| `llm_end` | LLM completes response | `{"content": "full response"}` |
| `node_start` | Graph node begins | `{"node": "model" \| "tools"}` |
| `node_end` | Graph node completes | `{"node": "model" \| "tools"}` |
| `tool_call` | Tool invocation | `{"tool": "name", "args": {...}, "id": "..."}` |
| `tool_result` | Tool returns | `{"tool": "name", "result": "...", "tool_call_id": "..."}` |
| `subagent_start` | SubAgent begins | `{"name": "agent_type", "description": "task"}` |
| `subagent_end` | SubAgent completes | `{"name": "agent_type", "result_preview": "..."}` |
| `subagent_tool_call` | SubAgent internal tool call | `{"subagent_name": "...", "tool": "...", "args": {...}, "id": "..."}` |
| `subagent_tool_result` | SubAgent internal tool result | `{"subagent_name": "...", "tool": "...", "result": "...", "tool_call_id": "..."}` |
| `error` | Error occurred | `{"message": "error description"}` |

---

## Event Data Structures

### llm_token

Real-time LLM output tokens. Format varies by provider:

```typescript
// Standard format (OpenAI)
{
  "event_type": "llm_token",
  "data": {
    "token": "Hello"
  }
}

// Anthropic format (content blocks)
{
  "event_type": "llm_token",
  "data": {
    "token": [
      {"text": "Hello", "type": "text", "index": 0}
    ]
  }
}

// Anthropic tool use streaming
{
  "event_type": "llm_token",
  "data": {
    "token": [
      {"partial_json": "{\"key\":", "type": "input_json_delta", "index": 1}
    ]
  }
}
```

### tool_call

```typescript
{
  "event_type": "tool_call",
  "data": {
    "tool": "web_search",
    "args": {
      "query": "latest news"
    },
    "id": "toolu_01ABCdef..."
  }
}
```

### tool_result

```typescript
{
  "event_type": "tool_result",
  "data": {
    "tool": "web_search",
    "result": "Search results: ...",
    "tool_call_id": "toolu_01ABCdef..."
  }
}
```

### subagent_start / subagent_end

```typescript
// subagent_start
{
  "event_type": "subagent_start",
  "data": {
    "name": "web_search_agent",
    "description": "Search for information about..."
  }
}

// subagent_end
{
  "event_type": "subagent_end",
  "data": {
    "name": "web_search_agent",
    "result_preview": "Based on my research... (truncated to 500 chars)"
  }
}
```

### subagent_tool_call / subagent_tool_result

These events are emitted when a SubAgent internally calls a tool:

```typescript
// subagent_tool_call
{
  "event_type": "subagent_tool_call",
  "data": {
    "subagent_name": "web_search_agent",
    "tool": "tavily_search",
    "args": {
      "query": "latest news about..."
    },
    "id": "toolu_01ABCdef..."
  }
}

// subagent_tool_result
{
  "event_type": "subagent_tool_result",
  "data": {
    "subagent_name": "web_search_agent",
    "tool": "tavily_search",
    "result": "Search results: ... (truncated to 500 chars)",
    "tool_call_id": "toolu_01ABCdef..."
  }
}
```

---

## Enabling SubAgent Events

By default, `subagent_start`, `subagent_end`, `subagent_tool_call`, and `subagent_tool_result` events are **disabled**. To enable:

```python
from src.middleware.subagent_middleware import CustomSubAgentMiddleware
from src.observation.outputs import ConsoleOutput, JsonFileOutput, CallbackOutput

# Create output handlers
outputs = [
    ConsoleOutput(verbose=True),
    JsonFileOutput("logs/run.json"),
]

# Enable subagent events via middleware
subagent_middleware = CustomSubAgentMiddleware(
    default_model=model,
    subagents=[search_agent_spec],
    stream_subagent_events=True,   # <-- Enable subagent events
    output_handlers=outputs,        # <-- Pass same handlers
)
```

When `stream_subagent_events=True`, the middleware will:
1. Emit `subagent_start` when a subagent begins execution
2. Stream `subagent_tool_call` and `subagent_tool_result` for each tool the subagent uses internally
3. Emit `subagent_end` when the subagent completes

---

## Frontend Integration Patterns

### Pattern 1: WebSocket (Real-time bidirectional)

```python
# Backend: FastAPI + WebSocket
from fastapi import WebSocket

connected_clients: list[WebSocket] = []

async def broadcast_event(event_type: str, data: dict):
    message = {"event_type": event_type, "data": data}
    for client in connected_clients:
        await client.send_json(message)

# Use CallbackOutput with async wrapper
def on_event(event_type: str, data: dict):
    asyncio.create_task(broadcast_event(event_type, data))

observer = AgentObserver([
    CallbackOutput(on_event),
])
```

```typescript
// Frontend: JavaScript WebSocket client
const ws = new WebSocket('ws://localhost:8000/ws');

ws.onmessage = (event) => {
  const { event_type, data } = JSON.parse(event.data);

  switch (event_type) {
    case 'llm_token':
      appendToOutput(extractToken(data.token));
      break;
    case 'tool_call':
      showToolIndicator(data.tool, data.args);
      break;
    case 'subagent_start':
      showSubAgentSpinner(data.name);
      break;
    case 'subagent_end':
      hideSubAgentSpinner(data.name);
      break;
  }
};

function extractToken(token: string | object[]): string {
  if (typeof token === 'string') return token;
  // Anthropic format
  return token
    .filter(b => b.type === 'text')
    .map(b => b.text)
    .join('');
}
```

### Pattern 2: Server-Sent Events (SSE)

```python
# Backend: FastAPI SSE
from fastapi import Response
from fastapi.responses import StreamingResponse
import json

async def event_generator():
    queue = asyncio.Queue()

    def on_event(event_type: str, data: dict):
        queue.put_nowait((event_type, data))

    observer = AgentObserver([CallbackOutput(on_event)])

    # Start agent in background
    task = asyncio.create_task(observer.arun(agent, inputs))

    while not task.done() or not queue.empty():
        try:
            event_type, data = await asyncio.wait_for(
                queue.get(), timeout=0.1
            )
            yield f"event: {event_type}\ndata: {json.dumps(data)}\n\n"
        except asyncio.TimeoutError:
            yield ": keepalive\n\n"

    yield f"event: done\ndata: {{}}\n\n"

@app.get("/stream")
async def stream():
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream"
    )
```

```typescript
// Frontend: EventSource
const eventSource = new EventSource('/stream');

eventSource.addEventListener('llm_token', (e) => {
  const data = JSON.parse(e.data);
  appendToOutput(extractToken(data.token));
});

eventSource.addEventListener('subagent_start', (e) => {
  const { name, description } = JSON.parse(e.data);
  showSubAgentCard(name, description);
});

eventSource.addEventListener('done', () => {
  eventSource.close();
});
```

### Pattern 3: Polling JSON File

For simpler setups, poll the JSON file:

```typescript
// Frontend: Polling
let lastEventCount = 0;

async function pollEvents() {
  const response = await fetch('/logs/run.json');
  const events = await response.json();

  // Process only new events
  const newEvents = events.slice(lastEventCount);
  lastEventCount = events.length;

  for (const event of newEvents) {
    handleEvent(event.event_type, event.data);
  }
}

setInterval(pollEvents, 500);
```

---

## Event Flow Timeline

```
User Query: "What's the weather in Tokyo?"
────────────────────────────────────────────────────────────────────

Time    Event                   Data
─────   ─────────────────────   ────────────────────────────────────
0.0s    llm_token              {"token": "I'll"}
0.1s    llm_token              {"token": " check"}
0.2s    llm_token              {"token": " the weather"}
0.3s    node_start             {"node": "model"}
0.3s    tool_call              {"tool": "task", "args": {...}}
0.3s    node_end               {"node": "model"}
        │
        │ (SubAgent executing - if stream_subagent_events=True)
        │
0.4s    subagent_start         {"name": "web_search_agent", ...}
        │
        │ (SubAgent internal work - streamed when enabled)
        │
1.0s    subagent_tool_call     {"subagent_name": "web_search_agent", "tool": "tavily_search", ...}
3.0s    subagent_tool_result   {"subagent_name": "web_search_agent", "tool": "tavily_search", ...}
        │
5.0s    subagent_end           {"name": "web_search_agent", ...}
        │
5.0s    llm_token              {"token": "Based on..."}  (result)
5.1s    node_start             {"node": "tools"}
5.1s    tool_result            {"tool": "task", "result": "..."}
5.1s    node_end               {"node": "tools"}
5.2s    llm_token              {"token": "The weather"}
5.3s    llm_token              {"token": " in Tokyo"}
...
6.0s    node_start             {"node": "model"}
6.0s    llm_end                {"content": "The weather in Tokyo..."}
6.0s    node_end               {"node": "model"}
```

---

## Output Handler Reference

### ConsoleOutput

```python
ConsoleOutput(
    verbose=True,      # Show node_start/end, llm_start
    show_tokens=True,  # Stream llm_token in real-time
)
```

### JsonFileOutput

```python
JsonFileOutput(
    file_path="logs/run.json",  # Auto-generates if None
)
# Writes immediately after each event
```

### CallbackOutput

```python
def my_callback(event_type: str, data: dict) -> None:
    # Handle event
    pass

CallbackOutput(callback=my_callback)
```

---

## Creating Custom OutputHandler

```python
from src.observation.outputs import OutputHandler

class WebSocketOutput(OutputHandler):
    def __init__(self, websocket):
        self.ws = websocket

    def emit(self, event_type: str, data: dict) -> None:
        asyncio.create_task(
            self.ws.send_json({
                "event_type": event_type,
                "data": data,
                "timestamp": datetime.now().isoformat(),
            })
        )

    def close(self) -> None:
        asyncio.create_task(self.ws.close())
```

---

## Best Practices

### 1. Token Extraction

Always handle both string and Anthropic array formats:

```python
def extract_token(token_data):
    if isinstance(token_data, str):
        return token_data
    if isinstance(token_data, list):
        return "".join(
            block.get("text", "")
            for block in token_data
            if block.get("type") == "text"
        )
    return ""
```

### 2. Buffering for UI

Buffer tokens before rendering to reduce DOM updates:

```typescript
let buffer = '';
let flushTimeout: number;

function onToken(token: string) {
  buffer += token;
  clearTimeout(flushTimeout);
  flushTimeout = setTimeout(() => {
    renderOutput(buffer);
    buffer = '';
  }, 50);
}
```

### 3. SubAgent Progress Indicators

Use `subagent_start`/`subagent_end` to show progress:

```typescript
function showSubAgentCard(name: string, description: string) {
  const card = document.createElement('div');
  card.id = `subagent-${name}`;
  card.innerHTML = `
    <div class="subagent-card loading">
      <span class="spinner"></span>
      <strong>${name}</strong>
      <p>${description}</p>
    </div>
  `;
  container.appendChild(card);
}

function hideSubAgentSpinner(name: string) {
  const card = document.getElementById(`subagent-${name}`);
  card?.classList.remove('loading');
}
```

---

## Limitations

1. **SubAgent LLM Token Streaming**: The intermediate LLM tokens from subagent execution are NOT propagated to the parent agent's stream. Only tool calls and results are streamed (when `stream_subagent_events=True`).

2. **Synchronous Callbacks**: `CallbackOutput.emit()` is synchronous. For async operations, use `asyncio.create_task()` inside the callback.

3. **Large Results**: `tool_result`, `subagent_end.result_preview`, and `subagent_tool_result.result` are truncated to 500 characters. Consider expanding in UI on user click.

---

## File References

- `src/observation/observer.py` - AgentObserver class
- `src/observation/outputs.py` - OutputHandler implementations
- `src/middleware/subagent_middleware.py` - SubAgent middleware with streaming toggle
