# Fullstack Chat Example

React + FastAPI example demonstrating real-time streaming chat with the AI agent.

## Features

- SSE (Server-Sent Events) streaming for real-time responses
- Token-by-token LLM output streaming
- Tool call and SubAgent status indicators with expandable details
- **Nested tool calls**: SubAgent internal tool calls are displayed in real-time
- **Stop button**: Cancel ongoing requests at any time
- Handles both OpenAI and Anthropic token formats

## Prerequisites

1. Set up environment variables in the project root `.env`:
   ```
   ANTHROPIC_API_KEY=sk-ant-...
   TAVILY_API_KEY=tvly-...
   ```

2. Install main project dependencies:
   ```bash
   cd /path/to/ai_agent_template
   uv sync
   ```

## Running the Backend

**Option 1: From project root (recommended)**
```bash
cd /path/to/ai_agent_template
uv run python examples/fullstack/backend/main.py
```

**Option 2: From backend directory**
```bash
cd examples/fullstack/backend
uv sync
uv run python main.py
```

The API will be available at http://localhost:8000

### API Endpoints

- `POST /api/chat/stream` - SSE streaming chat
- `GET /api/health` - Health check

## Running the Frontend

```bash
cd examples/fullstack/frontend
npm install
npm run dev
```

The UI will be available at http://localhost:5173

## Event Types

The streaming API emits these SSE events:

| Event | Description |
|-------|-------------|
| `llm_token` | LLM output token (streaming) |
| `llm_end` | LLM response complete |
| `tool_call` | Tool invocation started |
| `tool_result` | Tool returned result |
| `subagent_start` | SubAgent started |
| `subagent_end` | SubAgent completed |
| `subagent_tool_call` | SubAgent internal tool call |
| `subagent_tool_result` | SubAgent internal tool result |
| `error` | Error occurred |
| `done` | Stream complete |

## Project Structure

```
fullstack/
├── backend/
│   ├── main.py           # FastAPI app with SSE
│   ├── schemas.py        # Request/response models
│   └── pyproject.toml    # uv dependencies
└── frontend/
    ├── src/
    │   ├── App.tsx       # Main chat UI with ActivityCard components
    │   ├── App.css       # Styles including tool activity cards
    │   ├── types.ts      # TypeScript definitions (ToolActivity, etc.)
    │   └── hooks/
    │       └── useSSEChat.ts  # SSE streaming hook with stop support
    └── package.json
```

## UI Components

### Activity Cards with Side Panel

Tool and SubAgent activities are displayed as compact clickable cards below the AI message. Clicking a card opens a **Side Panel** on the right side showing detailed information:

- **Tool Card** (🔧): Shows tool name; click to see input arguments and output result in side panel
- **SubAgent Card** (🤖): Shows subagent name and tool count; click to see task description, nested tool calls, and final result in side panel

### Side Panel

When you click on an activity card, a side panel slides in from the right:

```
┌─────────────────────┬──────────────────────┐
│  AI Agent Chat      │  🤖 web_search_agent │
├─────────────────────┤  ─────────────────── │
│                     │  TASK:               │
│  [User message]     │  "Search for..."     │
│                     │                      │
│  [AI response...]   │  TOOL CALLS:         │
│                     │  ✓ 🔧 tavily_search  │
│  [🤖 task] (2) ▶   │  C 🔧 web_scrape     │
│                     │                      │
│                     │  RESULT:             │
│                     │  "Found information" │
└─────────────────────┴──────────────────────┘
```

Features:
- Auto-selects running SubAgent activities
- Real-time updates as tool calls complete
- Expandable nested tool details
- Click `✕` to close the panel

### Stop Button

Click the red "Stop" button to cancel an ongoing request. This aborts the SSE connection immediately.

## Reference Documentation

- [Streaming Output Guide](../../app_docs/streaming_output.md)
- [API Contract](../../app_docs/streaming_api_contract.md)
