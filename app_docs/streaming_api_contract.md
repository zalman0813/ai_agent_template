# Streaming API Contract

Frontend-Backend streaming API specification for real-time agent responses.

---

## Transport Options

| Method | Use Case | Pros | Cons |
|--------|----------|------|------|
| **SSE** | One-way streaming | Simple, auto-reconnect | One direction only |
| **WebSocket** | Bidirectional | Full duplex, low latency | More complex |
| **Polling** | Simple integration | Easy to implement | Higher latency |

**Recommendation:** Use SSE for chat streaming, WebSocket if you need bidirectional communication.

---

## TypeScript Interfaces

```typescript
// ===========================================
// Core Event Structure
// ===========================================

interface StreamEvent {
  event_type: EventType;
  timestamp: string;  // ISO 8601
  data: EventData;
}

type EventType =
  | "llm_token"
  | "llm_end"
  | "node_start"
  | "node_end"
  | "tool_call"
  | "tool_result"
  | "subagent_start"
  | "subagent_end"
  | "subagent_tool_call"
  | "subagent_tool_result"
  | "error"
  | "done";

// ===========================================
// Event Data Types
// ===========================================

interface LlmTokenData {
  token: string | ContentBlock[];
}

// Anthropic content block format
interface ContentBlock {
  type: "text" | "input_json_delta";
  text?: string;
  partial_json?: string;
  index: number;
}

interface LlmEndData {
  content: string;
}

interface NodeData {
  node: "model" | "tools";
}

interface ToolCallData {
  tool: string;
  args: Record<string, unknown>;
  id: string;
}

interface ToolResultData {
  tool: string;
  result: string;
  tool_call_id: string;
}

interface SubAgentStartData {
  name: string;
  description: string;
}

interface SubAgentEndData {
  name: string;
  result_preview: string;  // Truncated to 500 chars
}

// SubAgent internal tool call (nested within subagent execution)
interface SubAgentToolCallData {
  subagent_name: string;
  tool: string;
  args: Record<string, unknown>;
  id: string;
}

// SubAgent internal tool result (nested within subagent execution)
interface SubAgentToolResultData {
  subagent_name: string;
  tool: string;
  result: string;  // Truncated to 500 chars
  tool_call_id: string;
}

interface ErrorData {
  message: string;
  code?: string;
}

interface DoneData {
  final_response: string;
  usage?: {
    input_tokens: number;
    output_tokens: number;
  };
}

type EventData =
  | LlmTokenData
  | LlmEndData
  | NodeData
  | ToolCallData
  | ToolResultData
  | SubAgentStartData
  | SubAgentEndData
  | SubAgentToolCallData
  | SubAgentToolResultData
  | ErrorData
  | DoneData;
```

---

## SSE Stream Format

### Endpoint

```
POST /api/chat/stream
Content-Type: application/json

{
  "message": "What's the weather in Tokyo?",
  "session_id": "optional-session-id"
}

Response: text/event-stream
```

### Event Stream Example

```
event: llm_token
data: {"token":"I'll"}

event: llm_token
data: {"token":" check"}

event: llm_token
data: {"token":" the weather"}

event: node_start
data: {"node":"model"}

event: tool_call
data: {"tool":"task","args":{"subagent_type":"web_search_agent","description":"Search Tokyo weather"},"id":"toolu_123"}

event: node_end
data: {"node":"model"}

event: subagent_start
data: {"name":"web_search_agent","description":"Search Tokyo weather"}

event: subagent_tool_call
data: {"subagent_name":"web_search_agent","tool":"tavily_search","args":{"query":"Tokyo weather"},"id":"toolu_456"}

event: subagent_tool_result
data: {"subagent_name":"web_search_agent","tool":"tavily_search","result":"Tokyo: 22°C, sunny...","tool_call_id":"toolu_456"}

event: subagent_end
data: {"name":"web_search_agent","result_preview":"Current weather in Tokyo: 22°C, sunny..."}

event: node_start
data: {"node":"tools"}

event: tool_result
data: {"tool":"task","result":"Current weather in Tokyo: 22°C, sunny...","tool_call_id":"toolu_123"}

event: node_end
data: {"node":"tools"}

event: llm_token
data: {"token":"The weather"}

event: llm_token
data: {"token":" in Tokyo"}

event: llm_token
data: {"token":" is currently"}

event: llm_token
data: {"token":" 22°C and sunny."}

event: llm_end
data: {"content":"The weather in Tokyo is currently 22°C and sunny."}

event: done
data: {"final_response":"The weather in Tokyo is currently 22°C and sunny.","usage":{"input_tokens":50,"output_tokens":120}}
```

---

## Frontend Implementation

### SSE Client (Recommended)

```typescript
class ChatStreamClient {
  private eventSource: EventSource | null = null;
  private buffer = '';
  private flushTimeout: number | null = null;

  constructor(
    private onToken: (text: string) => void,
    private onToolCall: (tool: string, args: unknown) => void,
    private onSubAgentStart: (name: string, desc: string) => void,
    private onSubAgentEnd: (name: string) => void,
    private onDone: (response: string) => void,
    private onError: (message: string) => void,
  ) {}

  async send(message: string, sessionId?: string): Promise<void> {
    // Close existing connection
    this.close();

    // POST to get SSE stream
    const response = await fetch('/api/chat/stream', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message, session_id: sessionId }),
    });

    if (!response.ok) {
      this.onError(`HTTP ${response.status}`);
      return;
    }

    // Read SSE stream
    const reader = response.body?.getReader();
    const decoder = new TextDecoder();

    if (!reader) return;

    let buffer = '';
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() || '';

      let currentEvent = '';
      for (const line of lines) {
        if (line.startsWith('event: ')) {
          currentEvent = line.slice(7);
        } else if (line.startsWith('data: ')) {
          const data = JSON.parse(line.slice(6));
          this.handleEvent(currentEvent, data);
        }
      }
    }
  }

  private handleEvent(eventType: string, data: unknown): void {
    switch (eventType) {
      case 'llm_token':
        const { token } = data as LlmTokenData;
        this.bufferToken(this.extractToken(token));
        break;

      case 'tool_call':
        const toolCall = data as ToolCallData;
        this.onToolCall(toolCall.tool, toolCall.args);
        break;

      case 'subagent_start':
        const start = data as SubAgentStartData;
        this.onSubAgentStart(start.name, start.description);
        break;

      case 'subagent_end':
        const end = data as SubAgentEndData;
        this.onSubAgentEnd(end.name);
        break;

      case 'done':
        this.flushBuffer();
        const done = data as DoneData;
        this.onDone(done.final_response);
        break;

      case 'error':
        const error = data as ErrorData;
        this.onError(error.message);
        break;
    }
  }

  // Buffer tokens for smoother rendering
  private bufferToken(text: string): void {
    this.buffer += text;
    if (this.flushTimeout) clearTimeout(this.flushTimeout);
    this.flushTimeout = window.setTimeout(() => this.flushBuffer(), 50);
  }

  private flushBuffer(): void {
    if (this.buffer) {
      this.onToken(this.buffer);
      this.buffer = '';
    }
  }

  // Handle both OpenAI (string) and Anthropic (array) formats
  private extractToken(token: string | ContentBlock[]): string {
    if (typeof token === 'string') return token;
    return token
      .filter(b => b.type === 'text' && b.text)
      .map(b => b.text!)
      .join('');
  }

  close(): void {
    this.eventSource?.close();
    this.eventSource = null;
  }
}
```

### Usage Example

```typescript
const chat = new ChatStreamClient(
  // onToken
  (text) => {
    document.getElementById('output')!.textContent += text;
  },
  // onToolCall
  (tool, args) => {
    console.log(`Calling tool: ${tool}`, args);
    showToolIndicator(tool);
  },
  // onSubAgentStart
  (name, description) => {
    showSpinner(`SubAgent: ${name}`);
    console.log(`SubAgent starting: ${name} - ${description}`);
  },
  // onSubAgentEnd
  (name) => {
    hideSpinner();
    console.log(`SubAgent completed: ${name}`);
  },
  // onDone
  (response) => {
    console.log('Chat complete:', response);
    enableInput();
  },
  // onError
  (message) => {
    showError(message);
  }
);

// Send message
await chat.send("What's the weather in Tokyo?");
```

---

## Backend Implementation (FastAPI)

```python
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from src.observation.observer import AgentObserver
from src.observation.outputs import CallbackOutput
import asyncio
import json

app = FastAPI()

@app.post("/api/chat/stream")
async def chat_stream(request: ChatRequest):
    async def event_generator():
        queue = asyncio.Queue()

        def on_event(event_type: str, data: dict):
            queue.put_nowait((event_type, data))

        observer = AgentObserver([CallbackOutput(on_event)])

        # Run agent in background
        task = asyncio.create_task(
            observer.arun(agent, {"messages": [HumanMessage(request.message)]})
        )

        try:
            while not task.done() or not queue.empty():
                try:
                    event_type, data = await asyncio.wait_for(
                        queue.get(), timeout=0.1
                    )
                    yield f"event: {event_type}\ndata: {json.dumps(data)}\n\n"
                except asyncio.TimeoutError:
                    yield ": keepalive\n\n"

            # Get final result
            result = task.result()
            final_response = result.get("messages", [{}])[-1].content
            yield f"event: done\ndata: {json.dumps({'final_response': final_response})}\n\n"

        except Exception as e:
            yield f"event: error\ndata: {json.dumps({'message': str(e)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )
```

---

## Event Handling Quick Reference

| Event | When | Frontend Action |
|-------|------|-----------------|
| `llm_token` | LLM streaming | Append to output |
| `tool_call` | Tool invoked | Show tool activity card |
| `tool_result` | Tool returns | Update card with result |
| `subagent_start` | SubAgent begins | Show subagent card with spinner |
| `subagent_tool_call` | SubAgent calls tool | Add nested tool to subagent card |
| `subagent_tool_result` | SubAgent tool returns | Update nested tool with result |
| `subagent_end` | SubAgent done | Update subagent card with result |
| `error` | Error occurred | Show error message |
| `done` | Stream complete | Enable input, cleanup |

---

## Error Handling

```typescript
// Reconnection logic for SSE
let retryCount = 0;
const MAX_RETRIES = 3;

eventSource.onerror = (e) => {
  if (retryCount < MAX_RETRIES) {
    retryCount++;
    setTimeout(() => reconnect(), 1000 * retryCount);
  } else {
    showError('Connection failed. Please refresh.');
  }
};
```

---

## Non-Streaming Fallback

For environments that don't support SSE:

```typescript
// POST /api/chat
interface ChatResponse {
  success: boolean;
  data: {
    response: string;
    events: StreamEvent[];  // All events for debugging
    usage: {
      input_tokens: number;
      output_tokens: number;
    };
  };
}
```
