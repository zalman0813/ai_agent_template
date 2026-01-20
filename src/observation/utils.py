"""Utility functions for working with observation trace files."""

import json
from pathlib import Path
from typing import Any


def read_trace_file(file_path: str | Path) -> dict[str, Any]:
    """Read trace file and return metadata + events.

    Supports both formats:
    - Original format: Each line has "timestamp" and "event_type" fields
    - Optimized format: First line is metadata, events have "t" and "type" fields

    Args:
        file_path: Path to the trace file (JSONL format).

    Returns:
        Dictionary with "metadata", "events", and "format" keys:
        {
            "format": "optimized" or "original",
            "metadata": {
                "session_id": "...",
                "start_time": "2025-01-20T14:30:22.000000",
                "format_version": "2.0"
            },  # Only for optimized format
            "events": [
                {"t": 0.123456, "type": "node_start", "data": {...}},  # Optimized
                # or
                {"timestamp": "...", "event_type": "node_start", "data": {...}},  # Original
                ...
            ]
        }

    Example:
        >>> from src.observation.utils import read_trace_file
        >>> trace_data = read_trace_file("traces/abc123_session.json")
        >>> print(f"Format: {trace_data['format']}")
        >>> print(f"Total events: {len(trace_data['events'])}")
        >>> if trace_data['format'] == 'optimized':
        ...     print(f"Session started: {trace_data['metadata']['start_time']}")
    """
    file_path = Path(file_path)

    with file_path.open("r", encoding="utf-8") as f:
        lines = [line.strip() for line in f if line.strip()]

    if not lines:
        return {"format": "unknown", "metadata": {}, "events": []}

    # Parse first line to detect format
    first_line = json.loads(lines[0])

    # Check if it's optimized format (has "meta" marker)
    if first_line.get("meta") is True:
        # Optimized format
        metadata = first_line
        events = [json.loads(line) for line in lines[1:]]
        return {
            "format": "optimized",
            "metadata": metadata,
            "events": events,
        }
    else:
        # Original format (no metadata line, all lines are events)
        events = [json.loads(line) for line in lines]
        return {
            "format": "original",
            "metadata": {},
            "events": events,
        }
