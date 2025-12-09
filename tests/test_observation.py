"""Tests for the observation system.

Tests cover:
1. Basic event emission works
2. JsonFileOutput correctly logs events
3. ConsoleOutput displays events
4. Observer captures streaming from real LangGraph agent
"""

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from src.observation import AgentObserver, ConsoleOutput, JsonFileOutput, CallbackOutput


class TestJsonFileOutput:
    """Test JsonFileOutput handler."""

    def test_emit_creates_file(self):
        """Test that emitting events creates the JSON file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "test.json"
            output = JsonFileOutput(file_path)

            output.emit("test_event", {"key": "value"})
            output.close()

            assert file_path.exists()
            content = json.loads(file_path.read_text())
            assert len(content) == 1
            assert content[0]["event_type"] == "test_event"
            assert content[0]["data"]["key"] == "value"

    def test_emit_multiple_events(self):
        """Test emitting multiple events."""
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "test.json"
            output = JsonFileOutput(file_path)

            output.emit("node_start", {"node": "agent"})
            output.emit("tool_call", {"tool": "search", "args": {}})
            output.emit("node_end", {"node": "agent"})
            output.close()

            content = json.loads(file_path.read_text())
            assert len(content) == 3
            event_types = [e["event_type"] for e in content]
            assert event_types == ["node_start", "tool_call", "node_end"]


class TestConsoleOutput:
    """Test ConsoleOutput handler."""

    def test_emit_node_events(self, capsys):
        """Test console output for node events."""
        output = ConsoleOutput(verbose=True, show_tokens=False)

        output.emit("node_start", {"node": "test_node"})
        output.emit("node_end", {"node": "test_node"})

        captured = capsys.readouterr()
        assert "test_node" in captured.out
        assert ">>>" in captured.out  # node_start marker
        assert "<<<" in captured.out  # node_end marker

    def test_emit_tool_events(self, capsys):
        """Test console output for tool events."""
        output = ConsoleOutput(verbose=True, show_tokens=False)

        output.emit("tool_call", {"tool": "web_search", "args": {"query": "test"}})
        output.emit("tool_result", {"tool": "web_search", "result": "Result text"})

        captured = capsys.readouterr()
        assert "web_search" in captured.out
        assert "Tool Call" in captured.out
        assert "Tool Result" in captured.out

    def test_emit_llm_tokens(self, capsys):
        """Test streaming token output."""
        output = ConsoleOutput(verbose=False, show_tokens=True)

        output.emit("llm_token", {"token": "Hello"})
        output.emit("llm_token", {"token": " World"})

        captured = capsys.readouterr()
        assert "Hello World" in captured.out


class TestCallbackOutput:
    """Test CallbackOutput handler."""

    def test_callback_receives_events(self):
        """Test that callback receives all events."""
        events = []

        def callback(event_type, data):
            events.append((event_type, data))

        output = CallbackOutput(callback)

        output.emit("node_start", {"node": "agent"})
        output.emit("llm_token", {"token": "Hello"})
        output.emit("node_end", {"node": "agent"})

        assert len(events) == 3
        assert events[0] == ("node_start", {"node": "agent"})
        assert events[1] == ("llm_token", {"token": "Hello"})
        assert events[2] == ("node_end", {"node": "agent"})


class TestAgentObserver:
    """Test AgentObserver core functionality."""

    def test_emit_to_all_outputs(self):
        """Test that observer emits to all registered outputs."""
        mock1 = MagicMock()
        mock2 = MagicMock()

        observer = AgentObserver([mock1, mock2])
        observer.emit("test", {"data": "value"})

        mock1.emit.assert_called_once_with("test", {"data": "value"})
        mock2.emit.assert_called_once_with("test", {"data": "value"})

    def test_output_error_handling(self):
        """Test that errors in one output don't break others."""
        failing_output = MagicMock()
        failing_output.emit.side_effect = Exception("Output failed")

        working_output = MagicMock()

        observer = AgentObserver([failing_output, working_output])
        observer.emit("test", {"data": "value"})

        # Should still call the working output
        working_output.emit.assert_called_once_with("test", {"data": "value"})

    def test_process_ai_message_with_tool_calls(self):
        """Test processing AI message with tool calls."""
        events = []
        output = CallbackOutput(lambda t, d: events.append((t, d)))
        observer = AgentObserver([output])

        ai_msg = AIMessage(
            content="",
            tool_calls=[
                {"name": "search", "args": {"query": "test"}, "id": "call_123"}
            ]
        )

        observer._process_message(ai_msg)

        assert len(events) == 1
        assert events[0][0] == "tool_call"
        assert events[0][1]["tool"] == "search"

    def test_process_ai_message_with_content(self):
        """Test processing AI message with content."""
        events = []
        output = CallbackOutput(lambda t, d: events.append((t, d)))
        observer = AgentObserver([output])

        ai_msg = AIMessage(content="Final answer")

        observer._process_message(ai_msg)

        assert len(events) == 1
        assert events[0][0] == "llm_end"
        assert events[0][1]["content"] == "Final answer"

    def test_process_tool_message(self):
        """Test processing tool result message."""
        events = []
        output = CallbackOutput(lambda t, d: events.append((t, d)))
        observer = AgentObserver([output])

        tool_msg = ToolMessage(
            content="Search results...",
            name="search",
            tool_call_id="call_123"
        )

        observer._process_message(tool_msg)

        assert len(events) == 1
        assert events[0][0] == "tool_result"
        assert events[0][1]["tool"] == "search"
        assert events[0][1]["result"] == "Search results..."


class TestObserverHandleMessagesChunk:
    """Test _handle_messages_chunk specifically for different streaming formats."""

    def test_handle_string_token(self):
        """Test handling simple string token."""
        events = []
        output = CallbackOutput(lambda t, d: events.append((t, d)))
        observer = AgentObserver([output])

        # Create mock message chunk with string content
        mock_chunk = MagicMock()
        mock_chunk.content = "Hello"

        observer._handle_messages_chunk((mock_chunk, {}))

        assert len(events) == 1
        assert events[0][0] == "llm_token"
        assert events[0][1]["token"] == "Hello"

    def test_handle_list_content_blocks_extracts_text(self):
        """Test handling Anthropic-style content blocks as list.

        Anthropic returns content as a list of blocks like:
        [{"text": "Hello", "type": "text", "index": 0}]

        The observer should extract the text from these blocks.
        """
        events = []
        output = CallbackOutput(lambda t, d: events.append((t, d)))
        observer = AgentObserver([output])

        # Create mock with list content (Anthropic format)
        mock_chunk = MagicMock()
        mock_chunk.content = [{"text": "Hello", "type": "text", "index": 0}]

        observer._handle_messages_chunk((mock_chunk, {}))

        assert len(events) == 1
        assert events[0][0] == "llm_token"
        # Token should be the extracted text, not the whole list
        assert events[0][1]["token"] == "Hello"

    def test_handle_empty_content(self):
        """Test handling empty content gracefully."""
        events = []
        output = CallbackOutput(lambda t, d: events.append((t, d)))
        observer = AgentObserver([output])

        mock_chunk = MagicMock()
        mock_chunk.content = ""

        observer._handle_messages_chunk((mock_chunk, {}))

        # Should not emit for empty content
        assert len(events) == 0

    def test_handle_empty_list_content(self):
        """Test handling empty list content."""
        events = []
        output = CallbackOutput(lambda t, d: events.append((t, d)))
        observer = AgentObserver([output])

        mock_chunk = MagicMock()
        mock_chunk.content = []

        observer._handle_messages_chunk((mock_chunk, {}))

        # Should not emit for empty list
        assert len(events) == 0


class TestObserverIntegration:
    """Integration tests with mock LangGraph agent."""

    def test_run_captures_all_events(self):
        """Test that run() captures events from a mock agent stream."""
        events = []
        output = CallbackOutput(lambda t, d: events.append((t, d)))
        observer = AgentObserver([output])

        # Create a mock agent that yields realistic stream data
        mock_agent = MagicMock()

        # Simulate what LangGraph stream returns
        mock_agent.stream.return_value = [
            ("updates", {"agent": {"messages": [AIMessage(content="Thinking...")]}}),
            ("messages", (MagicMock(content="token1"), {})),
            ("messages", (MagicMock(content="token2"), {})),
            ("updates", {"agent": {"messages": [
                AIMessage(
                    content="",
                    tool_calls=[{"name": "search", "args": {"q": "test"}, "id": "1"}]
                )
            ]}}),
            ("updates", {"tools": {"messages": [
                ToolMessage(content="Result", name="search", tool_call_id="1")
            ]}}),
            ("updates", {"agent": {"messages": [AIMessage(content="Final answer")]}}),
        ]

        result = observer.run(mock_agent, {"messages": []})

        # Verify events were captured
        event_types = [e[0] for e in events]

        # Should have: node_start/end pairs, llm tokens, tool events
        assert "node_start" in event_types
        assert "node_end" in event_types
        assert "llm_token" in event_types
        assert "tool_call" in event_types
        assert "tool_result" in event_types
        assert "llm_end" in event_types


@pytest.fixture
def temp_log_dir():
    """Create a temporary directory for log files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)
