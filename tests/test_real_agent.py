"""End-to-end test for observation with real LangGraph agent.

This test verifies the observer works correctly with actual agent execution.
"""

import json
import os
import tempfile
from pathlib import Path

import pytest
from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent

from src.observation import AgentObserver, CallbackOutput, JsonFileOutput

# Load environment variables
load_dotenv()


@tool
def get_weather(city: str) -> str:
    """Get current weather for a city."""
    return f"The weather in {city} is sunny and 25°C."


@pytest.fixture
def simple_agent():
    """Create a simple test agent with a weather tool."""
    if not os.getenv("ANTHROPIC_API_KEY"):
        pytest.skip("ANTHROPIC_API_KEY not set")

    model = ChatAnthropic(model="claude-sonnet-4-20250514", temperature=0)
    return create_react_agent(model, [get_weather])


@pytest.fixture
def temp_log_path():
    """Create a temporary log file path."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir) / "test_observation.json"


class TestRealAgentObservation:
    """Test observation with real agent execution."""

    def test_observation_captures_events(self, simple_agent, temp_log_path):
        """Test that observer captures all event types from real execution."""
        events = []

        def capture_event(event_type, data):
            events.append({"type": event_type, "data": data})

        observer = AgentObserver([
            CallbackOutput(capture_event),
            JsonFileOutput(temp_log_path),
        ])

        # Run the agent with a query that uses the tool
        result = observer.run(
            simple_agent,
            {"messages": [HumanMessage(content="What's the weather in Tokyo?")]}
        )

        # Verify events were captured
        event_types = [e["type"] for e in events]
        print(f"\nCaptured events: {event_types}")

        # Should have node events
        assert "node_start" in event_types, "Missing node_start event"
        assert "node_end" in event_types, "Missing node_end event"

        # Should have tool events (since query requires tool use)
        assert "tool_call" in event_types, "Missing tool_call event"
        assert "tool_result" in event_types, "Missing tool_result event"

        # Verify tool call contains expected data
        tool_calls = [e for e in events if e["type"] == "tool_call"]
        assert len(tool_calls) > 0
        assert tool_calls[0]["data"]["tool"] == "get_weather"

        # Verify JSON file was written
        assert temp_log_path.exists()
        log_content = json.loads(temp_log_path.read_text())
        assert len(log_content) > 0

        # Verify token format is correct (string, not list)
        token_events = [e for e in log_content if e["event_type"] == "llm_token"]
        for token_event in token_events:
            token = token_event["data"]["token"]
            assert isinstance(token, str), f"Token should be string, got {type(token)}: {token}"
            print(f"Token: {token[:50]}..." if len(token) > 50 else f"Token: {token}")

    def test_observation_captures_llm_tokens(self, simple_agent, temp_log_path):
        """Test that LLM tokens are captured as strings."""
        events = []

        def capture_event(event_type, data):
            events.append({"type": event_type, "data": data})

        observer = AgentObserver([CallbackOutput(capture_event)])

        # Run with a simple query
        observer.run(
            simple_agent,
            {"messages": [HumanMessage(content="Say hello in exactly 3 words.")]}
        )

        # Check token events
        token_events = [e for e in events if e["type"] == "llm_token"]

        # Should have some tokens
        assert len(token_events) > 0, "No llm_token events captured"

        # All tokens should be strings
        for event in token_events:
            token = event["data"]["token"]
            assert isinstance(token, str), f"Token should be string, got: {type(token)}"

        print(f"\nCaptured {len(token_events)} token events")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
