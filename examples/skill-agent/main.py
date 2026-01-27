#!/usr/bin/env python3
"""Main entry point with manual middleware configuration.

This demonstrates:
1. Creating an agent with manual middleware configuration
2. Using CustomSubAgentMiddleware for subagent event visibility
3. Using LangGraph-style invocation
4. Event tracing with AgentObserver including subagent internal events
"""

import os
import sys
import uuid
from pathlib import Path

from dotenv import load_dotenv
from langgraph.checkpoint.memory import InMemorySaver

# Add parent directory to path for src imports
parent_dir = Path(__file__).parent.parent.parent
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))

from src.observation import AgentObserver, ConsoleOutput, SessionTraceOutput

from agent import create_skill_agent


def check_environment() -> bool:
    """Check required environment variables are set.

    Returns:
        True if all required variables are set.
    """
    required = [
        "AZURE_OPENAI_API_KEY",
        "AZURE_OPENAI_ENDPOINT",
        "AZURE_OPENAI_DEPLOYMENT_NAME",
    ]

    missing = [var for var in required if not os.environ.get(var)]

    if missing:
        print("Error: Missing required environment variables:")
        for var in missing:
            print(f"  - {var}")
        print("\nCopy .env.example to .env and fill in your values.")
        return False

    return True


def main():
    """Main entry point."""
    # Load environment variables
    load_dotenv()

    # Check environment
    if not check_environment():
        sys.exit(1)

    # Get paths from env or use defaults
    skills_root = os.environ.get("SKILLS_ROOT", "./skills")
    workspace_root = os.environ.get("WORKSPACE_ROOT", "./workspace")

    skills_path = Path(__file__).parent / skills_root
    workspace_path = Path(__file__).parent / workspace_root

    print(f"Loading skills from: {skills_path}")
    print(f"Workspace directory: {workspace_path}")

    try:
        # Create observer with console and session trace outputs
        trace_output = SessionTraceOutput(traces_dir="./traces")
        console_output = ConsoleOutput(verbose=True, show_tokens=True)
        observer = AgentObserver(outputs=[console_output, trace_output])

        # Create checkpointer for multi-turn conversation persistence
        checkpointer = InMemorySaver()

        # Create agent with output handlers for subagent event streaming
        agent = create_skill_agent(
            skills_root=skills_path,
            workspace_root=workspace_path,
            output_handlers=observer.outputs,  # Enable subagent event visibility
            checkpointer=checkpointer,  # Enable multi-turn conversation
        )

        # Generate unique thread_id for this session
        thread_id = str(uuid.uuid4())
        config = {"configurable": {"thread_id": thread_id}}

        # Display session info
        print(f"Session UUID: {trace_output.session_uuid}")
        print(f"Thread ID: {thread_id}")
        print(f"Traces will be saved to: {trace_output.trace_file}\n")

        # Chat loop
        print("=" * 50)
        print("Skill Agent POC (Deep Agents SDK)")
        print("=" * 50)
        print("Type 'quit' to exit")
        print("=" * 50 + "\n")

        while True:
            try:
                user_input = input("You: ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\nGoodbye!")
                print(f"Session trace saved: {trace_output.trace_file}")
                break

            if not user_input:
                continue

            if user_input.lower() == "quit":
                print("Goodbye!")
                print(f"Session trace saved: {trace_output.trace_file}")
                break

            # Run agent with observer for event tracing
            # Pass config with thread_id for multi-turn conversation persistence
            result = observer.run(
                agent,
                {"messages": [{"role": "user", "content": user_input}]},
                config=config,
            )

            # Get last message with defensive check
            if result and "messages" in result and result["messages"]:
                last_msg = result["messages"][-1]
                if hasattr(last_msg, "content"):
                    print(f"\nAgent: {last_msg.content}\n")
                else:
                    print(f"\nAgent: {last_msg}\n")
            else:
                print("\nAgent: [No response generated]\n")

    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
