"""End-to-end test for full workflow with TODO tools and web search subagent.

This test verifies:
1. Primary agent uses write_todo to create tasks
2. Primary agent delegates web search to web_search_agent subagent
3. Primary agent uses complete_todo after tasks are done
4. All events are properly logged via observation
"""

import json
import os
import tempfile
from pathlib import Path

import pytest
from dotenv import load_dotenv

from src.agents.primary_agent import create_primary_agent
from src.observation import AgentObserver, CallbackOutput, JsonFileOutput

# Load environment variables
load_dotenv()

# Path to todos file
TODOS_FILE = Path(__file__).parent.parent / "src" / "storage" / "todos.json"


@pytest.fixture
def clean_todos():
    """Clean up todos before test only (keep after for inspection)."""
    TODOS_FILE.parent.mkdir(parents=True, exist_ok=True)
    TODOS_FILE.write_text("[]")
    yield
    # Don't clean up after - allows inspection of results


@pytest.fixture
def temp_log_path():
    """Create a temporary log file path."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir) / "workflow_test.json"


class TestFullWorkflow:
    """Test complete workflow with TODO tools and subagent."""

    @pytest.mark.skipif(
        not os.getenv("ANTHROPIC_API_KEY") or not os.getenv("TAVILY_API_KEY"),
        reason="ANTHROPIC_API_KEY and TAVILY_API_KEY required"
    )
    def test_research_task_with_todos(self, clean_todos, temp_log_path):
        """Test a research task that requires breaking down into steps.

        The query is designed to:
        1. Trigger write_todo to create subtasks
        2. Trigger task tool to delegate to web_search_agent
        3. Trigger complete_todo after each subtask is done
        """
        events = []

        def capture_event(event_type, data):
            events.append({"type": event_type, "data": data})

        # Create primary agent with full capabilities
        agent = create_primary_agent()

        # Create observer
        observer = AgentObserver([
            CallbackOutput(capture_event),
            JsonFileOutput(temp_log_path),
        ])

        # This query is designed to trigger multiple tools and subagent
        query = """I need you to help me research and track progress on comparing
two AI coding assistants: GitHub Copilot and Cursor.

Please:
1. First, create TODO items for each comparison aspect you'll research
2. Search the web for the latest pricing information for both tools
3. Search for recent user reviews or comparisons from 2024-2025
4. Mark the TODOs as complete as you finish each research task
5. Give me a final summary

Make sure to track your progress with the TODO list!"""

        # Run the agent
        result = observer.run(
            agent,
            {"messages": [{"role": "user", "content": query}]}
        )

        # Analyze captured events
        event_types = [e["type"] for e in events]
        print(f"\n=== Captured Event Types ===")
        for et in sorted(set(event_types)):
            count = event_types.count(et)
            print(f"  {et}: {count}")

        # Check tool calls
        tool_calls = [e for e in events if e["type"] == "tool_call"]
        tool_names = [tc["data"].get("tool") for tc in tool_calls]
        print(f"\n=== Tool Calls ===")
        for tc in tool_calls:
            print(f"  {tc['data'].get('tool')}: {tc['data'].get('args', {})}")

        # Verify expected tools were called
        assert "write_todo" in tool_names, "write_todo should be called to create tasks"
        assert "task" in tool_names, "task tool should be called to delegate to subagent"

        # Check if complete_todo was called (may not always happen depending on agent behavior)
        if "complete_todo" in tool_names:
            print("\n[OK] complete_todo was called")
        else:
            print("\n[INFO] complete_todo was not called (agent may have different flow)")

        # Verify task tool was called with web_search_agent
        task_calls = [tc for tc in tool_calls if tc["data"].get("tool") == "task"]
        for tc in task_calls:
            args = tc["data"].get("args", {})
            print(f"\n=== Subagent Call ===")
            print(f"  Type: {args.get('subagent_type')}")
            print(f"  Description: {args.get('description', '')[:100]}...")

        # Verify JSON log was written
        assert temp_log_path.exists(), "JSON log file should be created"
        log_content = json.loads(temp_log_path.read_text())
        assert len(log_content) > 0, "Log should have events"

        # Verify all tokens are strings (not lists)
        token_events = [e for e in log_content if e["event_type"] == "llm_token"]
        for te in token_events:
            token = te["data"]["token"]
            assert isinstance(token, str), f"Token should be string: {token}"

        print(f"\n=== Log Summary ===")
        print(f"  Total events: {len(log_content)}")
        print(f"  Token events: {len(token_events)}")
        print(f"  Log file: {temp_log_path}")


# Simpler test that's more likely to trigger all tools
class TestSimpleTodoWorkflow:
    """Simpler tests for TODO workflow."""

    @pytest.mark.skipif(
        not os.getenv("ANTHROPIC_API_KEY") or not os.getenv("TAVILY_API_KEY"),
        reason="ANTHROPIC_API_KEY and TAVILY_API_KEY required"
    )
    def test_simple_todo_and_search(self, clean_todos, temp_log_path):
        """Test simple workflow: add todo -> search -> complete todo."""
        events = []

        def capture_event(event_type, data):
            events.append({"type": event_type, "data": data})

        agent = create_primary_agent()
        observer = AgentObserver([
            CallbackOutput(capture_event),
            JsonFileOutput(temp_log_path),
        ])

        # Very explicit query
        query = """Do these steps in order:
1. Use write_todo to add a task: "Research Tesla stock price"
2. Use the task tool to call web_search_agent to find Tesla's current stock price
3. Use complete_todo to mark task #1 as done
4. Tell me what you found"""

        result = observer.run(
            agent,
            {"messages": [{"role": "user", "content": query}]}
        )

        # Get tool calls
        tool_calls = [e for e in events if e["type"] == "tool_call"]
        tool_names = [tc["data"].get("tool") for tc in tool_calls]

        print(f"\n=== Tool Calls ({len(tool_calls)}) ===")
        for tc in tool_calls:
            tool = tc["data"].get("tool")
            args = tc["data"].get("args", {})
            print(f"  {tool}: {json.dumps(args, ensure_ascii=False)[:100]}")

        # These should definitely be called given explicit instructions
        assert "write_todo" in tool_names, "write_todo must be called"
        assert "task" in tool_names, "task tool must be called for subagent"
        assert "complete_todo" in tool_names, "complete_todo must be called"

        # Verify subagent type
        task_calls = [tc for tc in tool_calls if tc["data"].get("tool") == "task"]
        assert len(task_calls) > 0, "Should have task calls"

        for tc in task_calls:
            subagent_type = tc["data"].get("args", {}).get("subagent_type")
            print(f"\n  Subagent type: {subagent_type}")
            assert subagent_type == "web_search_agent", f"Should use web_search_agent, got {subagent_type}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
