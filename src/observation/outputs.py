"""Output handlers for agent observation.

Supports Console, JSON file, and Callback outputs.
"""

import json
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Any, Callable


class OutputHandler(ABC):
    """Base class for observation output handlers."""

    @abstractmethod
    def emit(self, event_type: str, data: dict[str, Any]) -> None:
        """Emit an observation event."""
        pass

    def close(self) -> None:
        """Clean up resources. Override if needed."""
        pass


class ConsoleOutput(OutputHandler):
    """Output observations to console with color formatting."""

    COLORS = {
        "node_start": "\033[94m",      # Blue
        "node_end": "\033[92m",        # Green
        "tool_call": "\033[93m",       # Yellow
        "tool_result": "\033[96m",     # Cyan
        "llm_start": "\033[95m",       # Magenta
        "llm_token": "\033[0m",        # Reset
        "llm_end": "\033[95m",         # Magenta
        "subagent_start": "\033[94m",  # Blue
        "subagent_end": "\033[92m",    # Green
        "error": "\033[91m",           # Red
        "reset": "\033[0m",
    }

    def __init__(self, verbose: bool = True, show_tokens: bool = True):
        """Initialize console output.

        Args:
            verbose: Show detailed output (node start/end, etc.)
            show_tokens: Stream LLM tokens in real-time
        """
        self.verbose = verbose
        self.show_tokens = show_tokens

    def emit(self, event_type: str, data: dict[str, Any]) -> None:
        """Print observation to console."""
        color = self.COLORS.get(event_type, self.COLORS["reset"])
        reset = self.COLORS["reset"]

        if event_type == "llm_token" and self.show_tokens:
            print(data.get("token", ""), end="", flush=True)
            return

        if event_type == "llm_end" and self.show_tokens:
            print()  # Newline after token stream

        if not self.verbose and event_type in ("node_start", "node_end", "llm_start"):
            return

        timestamp = datetime.now().strftime("%H:%M:%S")

        if event_type == "node_start":
            print(f"{color}[{timestamp}] >>> Node: {data.get('node')}{reset}")

        elif event_type == "node_end":
            print(f"{color}[{timestamp}] <<< Node: {data.get('node')}{reset}")

        elif event_type == "tool_call":
            tool_name = data.get("tool")
            args = json.dumps(data.get("args", {}), ensure_ascii=False)
            print(f"{color}[{timestamp}] Tool Call: {tool_name}{reset}")
            print(f"  Args: {args}")

        elif event_type == "tool_result":
            tool_name = data.get("tool")
            result = str(data.get("result", ""))[:200]
            print(f"{color}[{timestamp}] Tool Result: {tool_name}{reset}")
            print(f"  Result: {result}")

        elif event_type == "llm_start":
            print(f"{color}[{timestamp}] LLM Thinking...{reset}")

        elif event_type == "llm_end":
            if self.verbose:
                print(f"{color}[{timestamp}] LLM Done{reset}")

        elif event_type == "subagent_start":
            print(f"{color}[{timestamp}] >>> SubAgent: {data.get('name')}{reset}")

        elif event_type == "subagent_end":
            print(f"{color}[{timestamp}] <<< SubAgent: {data.get('name')}{reset}")

        elif event_type == "error":
            print(f"{color}[{timestamp}] Error: {data.get('message')}{reset}")


class JsonFileOutput(OutputHandler):
    """Output observations to a JSON file."""

    def __init__(self, file_path: str | Path | None = None):
        """Initialize JSON file output.

        Args:
            file_path: Path to output file. Auto-generates if None.
        """
        if file_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            file_path = Path(f"logs/observation_{timestamp}.json")

        self.file_path = Path(file_path)
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        self.events: list[dict] = []

    def emit(self, event_type: str, data: dict[str, Any]) -> None:
        """Append event to buffer and write immediately."""
        event = {
            "timestamp": datetime.now().isoformat(),
            "event_type": event_type,
            "data": data,
        }
        self.events.append(event)
        self._write()

    def _write(self) -> None:
        """Write events to file."""
        self.file_path.write_text(
            json.dumps(self.events, indent=2, ensure_ascii=False, default=str)
        )

    def close(self) -> None:
        """Final write on close."""
        self._write()


class CallbackOutput(OutputHandler):
    """Output observations via callback function for UI integration."""

    def __init__(self, callback: Callable[[str, dict[str, Any]], None]):
        """Initialize callback output.

        Args:
            callback: Function receiving (event_type, data) for each event.
        """
        self.callback = callback

    def emit(self, event_type: str, data: dict[str, Any]) -> None:
        """Call the callback with event data."""
        self.callback(event_type, data)
