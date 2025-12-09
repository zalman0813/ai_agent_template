# LangChain v1.0 Multi-Agent System Specification

## Overview
Build a multi-agent system using LangChain v1.0 `create_agent`:
- **Primary Agent**: Task manager with TODO tools
- **Subagent**: Web search capabilities via Tavily
- **Model**: Claude Sonnet 4.5 (`claude-sonnet-4-5-20250929`)

## Project Structure

```
ai_agent_template/
├── src/
│   ├── __init__.py
│   ├── main.py                 # Entry point
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── primary_agent.py    # Primary agent with TODO tools
│   │   └── search_agent.py     # Web search subagent
│   ├── tools/
│   │   ├── __init__.py
│   │   └── todo_tools.py       # TODO management tools
│   └── storage/
│       └── todos.json          # TODO data persistence
├── pyproject.toml              # uv package management
├── .env.example                # Environment variables template
└── .python-version             # Python version for uv
```

## Implementation Details

### 1. Package Management (pyproject.toml)

```toml
[project]
name = "langchain-multi-agent"
version = "0.1.0"
description = "Multi-agent system with LangChain v1.0"
requires-python = ">=3.10"
dependencies = [
    "langchain>=1.0.0",
    "langchain-anthropic>=0.3.0",
    "langchain-tavily>=0.1.0",
    "python-dotenv>=1.0.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "ruff>=0.4.0",
]

[tool.uv]
dev-dependencies = [
    "pytest>=8.0.0",
    "ruff>=0.4.0",
]
```

### 2. TODO Tools (`src/tools/todo_tools.py`)

```python
import json
from pathlib import Path
from langchain_core.tools import tool
from typing import Optional

TODOS_FILE = Path(__file__).parent.parent / "storage" / "todos.json"


def _load_todos() -> list[dict]:
    """Load todos from JSON file."""
    if not TODOS_FILE.exists():
        TODOS_FILE.parent.mkdir(parents=True, exist_ok=True)
        TODOS_FILE.write_text("[]")
        return []
    return json.loads(TODOS_FILE.read_text())


def _save_todos(todos: list[dict]) -> None:
    """Save todos to JSON file."""
    TODOS_FILE.write_text(json.dumps(todos, indent=2, ensure_ascii=False))


@tool
def write_todo(task: str, priority: str = "medium") -> str:
    """
    Add a new todo item to the list.

    Args:
        task: The task description
        priority: Priority level (low, medium, high)

    Returns:
        Confirmation message with the new todo ID
    """
    todos = _load_todos()
    new_id = len(todos) + 1
    new_todo = {
        "id": new_id,
        "task": task,
        "priority": priority,
        "completed": False
    }
    todos.append(new_todo)
    _save_todos(todos)
    return f"Added todo #{new_id}: {task} [Priority: {priority}]"


@tool
def list_todos(show_completed: bool = False) -> str:
    """
    List all todos.

    Args:
        show_completed: Whether to include completed todos

    Returns:
        Formatted list of todos
    """
    todos = _load_todos()
    if not show_completed:
        todos = [t for t in todos if not t["completed"]]

    if not todos:
        return "No todos found."

    lines = []
    for t in todos:
        status = "[x]" if t["completed"] else "[ ]"
        lines.append(f"{status} #{t['id']} [{t['priority']}] {t['task']}")
    return "\n".join(lines)


@tool
def complete_todo(todo_id: int) -> str:
    """
    Mark a todo as completed.

    Args:
        todo_id: The ID of the todo to complete

    Returns:
        Confirmation message
    """
    todos = _load_todos()
    for t in todos:
        if t["id"] == todo_id:
            t["completed"] = True
            _save_todos(todos)
            return f"Completed todo #{todo_id}: {t['task']}"
    return f"Todo #{todo_id} not found."
```

### 3. Web Search Subagent (`src/agents/search_agent.py`)

```python
from langchain.agents import create_agent
from langchain.chat_models import init_chat_model
from langchain_tavily import TavilySearch


def create_search_agent():
    """Create web search subagent."""
    model = init_chat_model(
        "claude-sonnet-4-5-20250929",
        model_provider="anthropic"
    )

    search_tool = TavilySearch(
        max_results=5,
        topic="general"
    )

    return create_agent(
        model=model,
        tools=[search_tool],
        system_prompt="""You are a web research specialist.
Your job is to search the web and find accurate, relevant information.
Always provide sources for the information you find.
Summarize findings clearly and concisely."""
    )
```

### 4. Primary Agent (`src/agents/primary_agent.py`)

```python
from langchain.agents import create_agent
from langchain.chat_models import init_chat_model
from deepagents.middleware.subagents import SubAgentMiddleware
from langchain_tavily import TavilySearch

from src.tools.todo_tools import write_todo, list_todos, complete_todo


def create_primary_agent():
    """Create primary agent with TODO tools and search subagent."""
    model = init_chat_model(
        "claude-sonnet-4-5-20250929",
        model_provider="anthropic",
        temperature=0.7
    )

    search_tool = TavilySearch(max_results=5, topic="general")

    return create_agent(
        model=model,
        tools=[write_todo, list_todos, complete_todo],
        system_prompt="""You are an intelligent task manager and research assistant.

Your capabilities:
1. Manage TODO lists - add, list, and complete tasks
2. Delegate web research to your web_search_agent subagent

Guidelines:
- When user asks to remember or track something, use write_todo
- When user needs current information from the web, delegate to web_search_agent
- Break complex tasks into smaller, manageable todos
- Always confirm actions taken""",
        middleware=[
            SubAgentMiddleware(
                default_model="claude-sonnet-4-5-20250929",
                subagents=[
                    {
                        "name": "web_search_agent",
                        "description": "Search the web for current information, news, and real-time data",
                        "system_prompt": "You are a web research specialist. Find accurate information quickly.",
                        "tools": [search_tool],
                    }
                ]
            )
        ]
    )
```

### 5. Main Entry Point (`src/main.py`)

```python
import os
from dotenv import load_dotenv
from src.agents.primary_agent import create_primary_agent


def main():
    # Load environment variables
    load_dotenv()

    # Verify API keys
    if not os.getenv("ANTHROPIC_API_KEY"):
        raise ValueError("ANTHROPIC_API_KEY not set")
    if not os.getenv("TAVILY_API_KEY"):
        raise ValueError("TAVILY_API_KEY not set")

    # Create agent
    agent = create_primary_agent()

    # Interactive loop
    print("Multi-Agent System Ready!")
    print("Commands: 'quit' to exit\n")

    while True:
        user_input = input("You: ").strip()
        if user_input.lower() in ["quit", "exit", "q"]:
            break

        if not user_input:
            continue

        result = agent.invoke({
            "messages": [{"role": "user", "content": user_input}]
        })

        print(f"\nAgent: {result['messages'][-1].content}\n")


if __name__ == "__main__":
    main()
```

### 6. Environment Variables (`.env.example`)

```env
# Anthropic API Key (required)
ANTHROPIC_API_KEY=your-anthropic-api-key

# Tavily API Key (required for web search)
# Get free key at: https://tavily.com
TAVILY_API_KEY=your-tavily-api-key
```

## Setup Instructions

```bash
# 1. Install uv (if not installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# 2. Create virtual environment and install dependencies
uv sync

# 3. Setup environment variables
cp .env.example .env
# Edit .env and add your API keys

# 4. Run the application
uv run python src/main.py
```

## API Keys Required

| Key | Purpose | Get it at |
|-----|---------|-----------|
| ANTHROPIC_API_KEY | Claude Sonnet 4.5 | https://console.anthropic.com |
| TAVILY_API_KEY | Web search | https://tavily.com (1000 free/month) |

## Usage Examples

```
You: Add a todo to review the quarterly report
Agent: Added todo #1: review the quarterly report [Priority: medium]

You: Search for the latest AI news
Agent: [Delegates to web_search_agent, returns summarized results]

You: List my todos
Agent: [ ] #1 [medium] review the quarterly report

You: Complete todo 1
Agent: Completed todo #1: review the quarterly report
```

## Notes

- LangChain v1.0 uses `langchain.agents.create_agent` (not `langgraph.prebuilt.create_react_agent`)
- SubAgentMiddleware handles automatic task delegation to subagents
- TODO data persists in `src/storage/todos.json`
- Each subagent has isolated context for security
