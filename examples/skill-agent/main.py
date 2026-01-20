#!/usr/bin/env python3
"""Main entry point using Deep Agents SDK.

This demonstrates:
1. Creating an agent with Deep Agents SDK
2. Using LangGraph-style invocation
3. Automatic middleware handling
"""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

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
        # Create agent (returns CompiledStateGraph)
        agent = create_skill_agent(
            skills_root=skills_path,
            workspace_root=workspace_path,
        )

        # Chat loop
        print("\n" + "=" * 50)
        print("Skill Agent POC (Deep Agents SDK)")
        print("=" * 50)
        print("Type 'quit' to exit")
        print("=" * 50 + "\n")

        while True:
            try:
                user_input = input("You: ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\nGoodbye!")
                break

            if not user_input:
                continue

            if user_input.lower() == "quit":
                print("Goodbye!")
                break

            # LangGraph-style invocation
            result = agent.invoke({
                "messages": [{"role": "user", "content": user_input}]
            })

            # Get last message
            last_msg = result["messages"][-1]
            print(f"\nAgent: {last_msg.content}\n")

    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
