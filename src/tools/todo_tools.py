import json
from pathlib import Path

from langchain_core.tools import tool

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
