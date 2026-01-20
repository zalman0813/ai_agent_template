# Agent Observation System

## Overview

The observation module (`src/observation/`) provides real-time streaming observation for LangGraph agents, allowing you to capture, monitor, and persist all agent execution events including tool calls, LLM responses, node execution, and errors.

## Purpose

- **Debugging**: Track agent behavior and decision-making in real-time
- **Logging**: Persist execution traces for post-mortem analysis
- **Monitoring**: Stream events to consoles, files, or custom handlers
- **UI Integration**: Feed events to user interfaces via callbacks
- **Session Tracking**: Maintain isolated trace files per conversation session

## Architecture

The observation system consists of two main components:

### 1. AgentObserver

The central orchestrator that wraps LangGraph agent execution and captures events from the event stream.

**Key Features:**
- Non-intrusive: Works with any LangGraph `CompiledStateGraph`
- Multi-output: Broadcast events to multiple handlers simultaneously
- Event streaming: Captures events in real-time as they occur
- Clean API: Simple `run()` method replaces direct `agent.invoke()`

### 2. OutputHandler (Base Class)

Abstract base class for creating custom output destinations. All handlers implement:
- `emit(event_type: str, data: dict)`: Process a single event
- `close()`: Optional cleanup on completion

## Available Output Handlers

### ConsoleOutput

Displays events in the terminal with color-coded formatting.

**Features:**
- Color-coded events (blue for nodes, yellow for tools, cyan for results)
- Configurable verbosity levels
- Optional LLM token streaming
- Timestamp display

**Example:**
```python
from src.observation import AgentObserver, ConsoleOutput

console = ConsoleOutput(verbose=True, show_tokens=True)
observer = AgentObserver(outputs=[console])
result = observer.run(agent, {"messages": [{"role": "user", "content": "Hello"}]})
```

**Output:**
```
[14:30:22] >>> Node: agent
[14:30:22] Tool Call: read_file
  Args: {"path": "/workspace/sample.csv"}
[14:30:22] Tool Result: read_file
  Result: name,age,city,salary...
[14:30:23] <<< Node: agent
```

### JsonFileOutput

Saves all events to a single JSON file with automatic timestamping.

**Features:**
- Auto-generates filename with timestamp
- Pretty-printed JSON with indentation
- Creates log directory automatically
- Immediate writes on each event

**Example:**
```python
from src.observation import AgentObserver, JsonFileOutput

json_output = JsonFileOutput(file_path="logs/session.json")
observer = AgentObserver(outputs=[json_output])
result = observer.run(agent, inputs)
```

**Output Format:**
```json
[
  {
    "timestamp": "2025-01-20T14:30:22.123456",
    "event_type": "tool_call",
    "data": {
      "tool": "read_file",
      "args": {"path": "/workspace/sample.csv"},
      "id": "call_1"
    }
  },
  {
    "timestamp": "2025-01-20T14:30:22.234567",
    "event_type": "tool_result",
    "data": {
      "tool": "read_file",
      "result": "name,age,city,salary\n...",
      "tool_call_id": "call_1"
    }
  }
]
```

### SessionTraceOutput

Creates session-isolated JSONL trace files with unique UUIDs for each conversation.

**Features:**
- Unique UUID per session
- JSONL format (one JSON object per line)
- Full ISO 8601 timestamps for complete timing information
- Efficient append-mode writes
- Session ID and trace file path properties
- Configurable traces directory

**Example:**
```python
from src.observation import AgentObserver, SessionTraceOutput, ConsoleOutput

trace_output = SessionTraceOutput(traces_dir="./traces")
console_output = ConsoleOutput(verbose=True, show_tokens=True)
observer = AgentObserver(outputs=[console_output, trace_output])

print(f"Session UUID: {trace_output.session_uuid}")
print(f"Trace file: {trace_output.trace_file}")

result = observer.run(agent, inputs)
```

**Output Format (JSONL):**
```jsonl
{"timestamp": "2025-01-20T14:30:22.123456", "event_type": "node_start", "data": {"node": "agent"}}
{"timestamp": "2025-01-20T14:30:22.234567", "event_type": "tool_call", "data": {"tool": "read_file", "args": {"path": "/workspace/sample.csv"}, "id": "call_1"}}
{"timestamp": "2025-01-20T14:30:22.345678", "event_type": "tool_result", "data": {"tool": "read_file", "result": "name,age,city,salary\n...", "tool_call_id": "call_1"}}
{"timestamp": "2025-01-20T14:30:23.456789", "event_type": "node_end", "data": {"node": "agent"}}
```

**File Naming:**
- Pattern: `{uuid}_session.json`
- Example: `a1b2c3d4-5e6f-7890-abcd-ef1234567890_session.json`

**Optimizing Trace Files:**
For large trace files that exceed token limits, you can optimize them using the conversion script:

```bash
# Optimize a single trace file (creates <filename>_optimized.json)
python tools/optimize_trace.py traces/abc123_session.json

# Specify output filename
python tools/optimize_trace.py traces/abc123_session.json traces/abc123_opt.json
```

The optimization script converts full ISO timestamps to relative timestamps (seconds since session start), reducing token consumption by ~50%. See "Trace File Optimization" section below for details.

**Reading Trace Files:**
Use the `read_trace_file` utility to parse trace files (supports both original and optimized formats):

```python
from src.observation import read_trace_file

trace_data = read_trace_file("traces/a1b2c3d4-..._session.json")

# Check format
print(f"Format: {trace_data['format']}")  # 'original' or 'optimized'
print(f"Total events: {len(trace_data['events'])}")

# Access metadata (only available for optimized format)
if trace_data['format'] == 'optimized':
    print(f"Session ID: {trace_data['metadata']['session_id']}")
    print(f"Session started: {trace_data['metadata']['start_time']}")

# Access events
for event in trace_data['events']:
    if trace_data['format'] == 'optimized':
        print(f"At t={event['t']:.6f}s: {event['type']}")
    else:
        print(f"At {event['timestamp']}: {event['event_type']}")
```

### CallbackOutput

Executes custom callback functions for UI integration or custom processing.

**Features:**
- Direct function calls for each event
- Ideal for UI frameworks (Streamlit, Gradio, custom web apps)
- Zero latency event processing
- Full event data access

**Example:**
```python
from src.observation import AgentObserver, CallbackOutput

def handle_event(event_type: str, data: dict):
    if event_type == "tool_call":
        print(f"Tool called: {data['tool']}")
    elif event_type == "llm_end":
        print(f"LLM response: {data['content'][:100]}...")

callback_output = CallbackOutput(callback=handle_event)
observer = AgentObserver(outputs=[callback_output])
result = observer.run(agent, inputs)
```

## Event Types

The observation system captures the following event types:

| Event Type | Description | Data Fields |
|------------|-------------|-------------|
| `node_start` | LangGraph node begins execution | `node` (str) |
| `node_end` | LangGraph node completes execution | `node` (str) |
| `tool_call` | Agent invokes a tool | `tool` (str), `args` (dict), `id` (str) |
| `tool_result` | Tool execution completes | `tool` (str), `result` (any), `tool_call_id` (str) |
| `llm_start` | LLM begins processing | `messages` (list) |
| `llm_token` | LLM streams a token | `token` (str) |
| `llm_end` | LLM completes response | `content` (str) |
| `subagent_start` | Sub-agent begins execution | `name` (str) |
| `subagent_end` | Sub-agent completes execution | `name` (str) |
| `error` | Execution error occurs | `message` (str), `exception` (str) |

## Usage Examples

### Basic Console Monitoring

```python
from src.observation import AgentObserver, ConsoleOutput
from agent import create_skill_agent

# Create agent
agent = create_skill_agent(skills_root="./skills", workspace_root="./workspace")

# Create observer with console output
observer = AgentObserver(outputs=[ConsoleOutput(verbose=True)])

# Run with observation
result = observer.run(agent, {
    "messages": [{"role": "user", "content": "Analyze sample.csv"}]
})
```

### Session-Based Tracing

```python
from src.observation import AgentObserver, SessionTraceOutput, ConsoleOutput

# Create outputs
trace_output = SessionTraceOutput(traces_dir="./traces")
console_output = ConsoleOutput(verbose=True, show_tokens=True)

# Create observer with multiple outputs
observer = AgentObserver(outputs=[console_output, trace_output])

# Display session info
print(f"Session UUID: {trace_output.session_uuid}")
print(f"Trace file: {trace_output.trace_file}")

# Run agent
result = observer.run(agent, inputs)

# Trace file is automatically saved at: ./traces/{uuid}_session.json
print(f"Session trace saved: {trace_output.trace_file}")
```

### Custom Callback Integration

```python
from src.observation import AgentObserver, CallbackOutput

class UIEventHandler:
    def __init__(self):
        self.events = []

    def handle_event(self, event_type: str, data: dict):
        self.events.append({"type": event_type, "data": data})

        # Update UI based on event type
        if event_type == "tool_call":
            self.update_tool_status(data["tool"])
        elif event_type == "llm_end":
            self.display_response(data["content"])

    def update_tool_status(self, tool_name: str):
        print(f"[UI] Tool active: {tool_name}")

    def display_response(self, content: str):
        print(f"[UI] Agent response: {content}")

# Create handler and observer
ui_handler = UIEventHandler()
observer = AgentObserver(outputs=[
    CallbackOutput(callback=ui_handler.handle_event)
])

# Run agent
result = observer.run(agent, inputs)

# Access collected events
print(f"Total events captured: {len(ui_handler.events)}")
```

### Multi-Output Configuration

Combine multiple outputs for comprehensive observability:

```python
from src.observation import (
    AgentObserver,
    ConsoleOutput,
    SessionTraceOutput,
    JsonFileOutput,
    CallbackOutput
)

# Create multiple outputs
console = ConsoleOutput(verbose=True, show_tokens=True)
session_trace = SessionTraceOutput(traces_dir="./traces")
full_log = JsonFileOutput(file_path="logs/full_session.json")
callback = CallbackOutput(callback=lambda t, d: print(f"Event: {t}"))

# Combine all outputs
observer = AgentObserver(outputs=[console, session_trace, full_log, callback])

# All outputs receive every event simultaneously
result = observer.run(agent, inputs)
```

## Integration Guide for Examples

### Adding Observation to Existing Examples

1. **Add parent directory to Python path** (for examples importing from `src/`):
   ```python
   import sys
   from pathlib import Path

   parent_dir = Path(__file__).parent.parent.parent
   if str(parent_dir) not in sys.path:
       sys.path.insert(0, str(parent_dir))
   ```

2. **Import observation components**:
   ```python
   from src.observation import AgentObserver, ConsoleOutput, SessionTraceOutput, read_trace_file
   ```

3. **Create observer with desired outputs**:
   ```python
   trace_output = SessionTraceOutput(traces_dir="./traces")
   console_output = ConsoleOutput(verbose=True, show_tokens=True)
   observer = AgentObserver(outputs=[console_output, trace_output])
   ```

4. **Replace direct invocation with observer**:
   ```python
   # Before:
   result = agent.invoke({"messages": [{"role": "user", "content": user_input}]})

   # After:
   result = observer.run(agent, {"messages": [{"role": "user", "content": user_input}]})
   ```

5. **Display session info**:
   ```python
   print(f"Session UUID: {trace_output.session_uuid}")
   print(f"Traces will be saved to: {trace_output.trace_file}")
   ```

### Example: skill-agent Integration

See `examples/skill-agent/main.py` for a complete integration example with:
- Session-based trace files in `traces/` directory
- Real-time console output with colors
- Session UUID display
- Trace file path shown on exit

## API Reference

### AgentObserver

```python
class AgentObserver:
    def __init__(self, outputs: list[OutputHandler] | None = None):
        """Initialize observer with output handlers.

        Args:
            outputs: List of output handlers to receive events.
                    Defaults to [ConsoleOutput()] if None.
        """

    def run(self, agent: CompiledStateGraph, inputs: dict) -> dict:
        """Run agent with observation.

        Args:
            agent: LangGraph compiled agent
            inputs: Input dictionary for agent.invoke()

        Returns:
            Agent execution result (same as agent.invoke())
        """

    def close(self):
        """Close all output handlers."""
```

### OutputHandler

```python
class OutputHandler(ABC):
    @abstractmethod
    def emit(self, event_type: str, data: dict[str, Any]) -> None:
        """Emit an observation event.

        Args:
            event_type: Type of event (e.g., 'tool_call', 'llm_end')
            data: Event-specific data dictionary
        """

    def close(self) -> None:
        """Clean up resources. Override if needed."""
```

### ConsoleOutput

```python
class ConsoleOutput(OutputHandler):
    def __init__(self, verbose: bool = True, show_tokens: bool = True):
        """Initialize console output.

        Args:
            verbose: Show detailed output (node start/end, etc.)
            show_tokens: Stream LLM tokens in real-time
        """
```

### JsonFileOutput

```python
class JsonFileOutput(OutputHandler):
    def __init__(self, file_path: str | Path | None = None):
        """Initialize JSON file output.

        Args:
            file_path: Path to output file. Auto-generates if None.
        """
```

### SessionTraceOutput

```python
class SessionTraceOutput(OutputHandler):
    def __init__(self, traces_dir: str | Path = "./traces"):
        """Initialize session trace output.

        Args:
            traces_dir: Directory to store trace files. Defaults to './traces'.
        """

    @property
    def session_uuid(self) -> str:
        """Get the session UUID."""

    @property
    def trace_file(self) -> Path:
        """Get the trace file path."""
```

### CallbackOutput

```python
class CallbackOutput(OutputHandler):
    def __init__(self, callback: Callable[[str, dict[str, Any]], None]):
        """Initialize callback output.

        Args:
            callback: Function receiving (event_type, data) for each event.
        """
```

### read_trace_file

```python
def read_trace_file(file_path: str | Path) -> dict[str, Any]:
    """Read trace file and return metadata + events.

    Args:
        file_path: Path to the trace file (JSONL format).

    Returns:
        Dictionary with "metadata" and "events" keys:
        {
            "metadata": {
                "session_id": "...",
                "start_time": "2025-01-20T14:30:22.000000",
                "format_version": "2.0"
            },
            "events": [
                {"t": 0.123456, "type": "node_start", "data": {...}},
                {"t": 0.234567, "type": "tool_call", "data": {...}},
                ...
            ]
        }

    Example:
        >>> from src.observation import read_trace_file
        >>> trace_data = read_trace_file("traces/abc123_session.json")
        >>> print(f"Session started: {trace_data['metadata']['start_time']}")
        >>> print(f"Total events: {len(trace_data['events'])}")
    """
```

## Trace File Optimization

For large trace files that exceed LLM token limits or need to be analyzed by AI models, you can optimize them using the `tools/optimize_trace.py` script.

### What It Does

The optimization script converts trace files from the verbose format with full ISO 8601 timestamps to an optimized format with relative timestamps:

**Before (Original Format):**
```jsonl
{"timestamp": "2025-01-20T14:30:22.123456", "event_type": "node_start", "data": {...}}
{"timestamp": "2025-01-20T14:30:22.234567", "event_type": "tool_call", "data": {...}}
```

**After (Optimized Format):**
```jsonl
{"meta": true, "session_id": "abc123", "start_time": "2025-01-20T14:30:22.123456", "format_version": "2.0"}
{"t": 0.0, "type": "node_start", "data": {...}}
{"t": 0.111111, "type": "tool_call", "data": {...}}
```

### Token Savings

- **Timestamp field**: `"timestamp": "2025-01-20T14:30:22.123456"` (48 chars) → `"t": 0.123456` (14 chars)
- **Event type field**: `"event_type"` (12 chars) → `"type"` (6 chars)
- **Per event reduction**: ~40 characters (~10 tokens)
- **For 733 events**: ~36,000 tokens → ~18,000 tokens (**50% reduction**)

### Usage

```bash
# Basic usage (creates <filename>_optimized.json)
python tools/optimize_trace.py traces/abc123_session.json

# Specify output filename
python tools/optimize_trace.py traces/abc123_session.json traces/abc123_opt.json

# Process all trace files in a directory
for f in traces/*.json; do
    python tools/optimize_trace.py "$f"
done

# Quiet mode (no output, only errors)
python tools/optimize_trace.py -q traces/abc123_session.json
```

### Output

```
✅ Trace file optimized successfully!

Input:  traces/abc123_session.json
Output: traces/abc123_session_optimized.json

Events: 733

File size:
  Before: 145,234 bytes
  After:  72,891 bytes
  Saved:  49.8%

Estimated tokens (1 token ≈ 4 chars):
  Before: ~36,308 tokens
  After:  ~18,222 tokens
  Saved:  49.8%
```

### Optimized Format Details

**Metadata Line (First Line):**
- `meta: true` - Marker to identify metadata line
- `session_id` - Unique session identifier
- `start_time` - Absolute ISO 8601 timestamp of session start
- `format_version: "2.0"` - Format version marker

**Event Lines:**
- `t` - Relative timestamp (seconds.microseconds since session start)
- `type` - Event type (shortened from `event_type`)
- `data` - Event data (unchanged)

**Converting Back to Absolute Time:**
```python
from datetime import datetime, timedelta

# Parse metadata
start_time = datetime.fromisoformat(metadata['start_time'])

# Convert relative to absolute
for event in events:
    absolute_time = start_time + timedelta(seconds=event['t'])
    print(f"{absolute_time.isoformat()}: {event['type']}")
```

## Best Practices

1. **Use SessionTraceOutput for production**: Provides isolated, append-efficient trace files
2. **Optimize large traces**: Use `tools/optimize_trace.py` when files exceed token limits or need AI analysis
3. **Combine console and trace outputs**: Get real-time feedback plus persistent logs
4. **Filter verbose events**: Set `verbose=False` on ConsoleOutput to reduce noise
5. **Disable token streaming for performance**: Set `show_tokens=False` if not needed
6. **Custom callbacks for UI**: Use CallbackOutput to integrate with web frameworks
7. **Use read_trace_file for analysis**: Parse both original and optimized formats with the provided utility
8. **Clean up observers**: Call `observer.close()` when done (or use context managers)

## Troubleshooting

**Q: Events not appearing in trace file?**
- Check that the traces directory exists and is writable
- Verify observer.run() completed successfully
- Ensure SessionTraceOutput was added to observer outputs

**Q: Console output too noisy?**
- Set `verbose=False` on ConsoleOutput
- Set `show_tokens=False` to disable LLM streaming
- Filter events in custom CallbackOutput

**Q: Missing events in trace?**
- Ensure agent uses LangGraph's event streaming API
- Check that all tools are properly instrumented
- Verify observer.run() is used instead of agent.invoke()

**Q: Import errors in examples?**
- Ensure parent directory is added to sys.path
- Check that `src/` module structure is intact
- Verify relative imports use correct paths
