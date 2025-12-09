"""Todo Middleware for persistent JSON-based task management.

This middleware provides a write_todos/read_todos pattern inspired by
LangChain Deep Agents and Claude Code's TodoWrite design.

The agent maintains the entire todo list state and overwrites it
with each write_todos call, allowing atomic updates to the full list.
"""

import json
from pathlib import Path

from langchain.agents.middleware.types import AgentMiddleware, ModelRequest, ModelResponse
from langchain_core.tools import StructuredTool

# Default storage path
DEFAULT_TODOS_FILE = Path(__file__).parent.parent / "storage" / "todos.json"

# System prompt explaining todo tool usage
TODO_SYSTEM_PROMPT = """## Task Management

You have access to todo list tools for tracking task progress:

- `write_todos(todos)`: Write the entire todo list. Each todo requires:
  - content: Task description (imperative form, e.g., "Run tests")
  - status: "pending", "in_progress", or "completed"
  - activeForm: Present continuous form (e.g., "Running tests")

- `read_todos()`: Read current todo list state

**When to use:**
- Complex multi-step tasks requiring planning
- Breaking down large requests into trackable items
- Showing progress to the user

**Best practices:**
- Keep exactly ONE task as "in_progress" at a time
- Mark tasks "completed" immediately when done
- Update the entire list with each write (not individual items)
- Always provide both content and activeForm:
  - content: "Fix authentication bug"
  - activeForm: "Fixing authentication bug"

**When NOT to use:**
- Simple single-step tasks
- Quick questions or explanations
"""


class TodoMiddleware(AgentMiddleware):
    """Middleware providing persistent JSON-based todo management.

    Features:
    - Stores todos in JSON file for persistence
    - Injects system prompt with usage instructions
    - Provides write_todos and read_todos tools
    - Atomic list updates (overwrites entire list each time)

    Example:
        ```python
        from langchain.agents import create_agent
        from src.middleware import TodoMiddleware

        agent = create_agent(
            model,
            tools=[],
            middleware=[TodoMiddleware()],
        )
        ```
    """

    def __init__(
        self,
        todos_file: Path | str | None = None,
        system_prompt: str | None = TODO_SYSTEM_PROMPT,
    ):
        """Initialize TodoMiddleware.

        Args:
            todos_file: Path to JSON file for storing todos.
                       Defaults to src/storage/todos.json
            system_prompt: System prompt explaining tool usage.
                          Set to None to disable prompt injection.
        """
        super().__init__()
        self.todos_file = Path(todos_file) if todos_file else DEFAULT_TODOS_FILE
        self.system_prompt = system_prompt

        # Ensure storage directory exists
        self.todos_file.parent.mkdir(parents=True, exist_ok=True)
        if not self.todos_file.exists():
            self.todos_file.write_text("[]")

        # Create tools
        self.tools = self._create_tools()

    def _load_todos(self) -> list[dict]:
        """Load todos from JSON file."""
        if not self.todos_file.exists():
            return []
        try:
            return json.loads(self.todos_file.read_text())
        except json.JSONDecodeError:
            return []

    def _save_todos(self, todos: list[dict]) -> None:
        """Save todos to JSON file."""
        self.todos_file.write_text(json.dumps(todos, indent=2, ensure_ascii=False))

    def _create_tools(self) -> list[StructuredTool]:
        """Create todo tools bound to this middleware's storage."""

        def write_todos(todos: list[dict]) -> str:
            """Write the entire todo list at once.

            Args:
                todos: List of todo items, each with:
                    - content (str): Task description (imperative form, e.g., "Run tests")
                    - status (str): "pending", "in_progress", or "completed"
                    - activeForm (str): Present continuous form (e.g., "Running tests")

            Returns:
                Confirmation message with summary
            """
            # Validate required fields and status values
            valid_statuses = {"pending", "in_progress", "completed"}
            required_fields = {"content", "status", "activeForm"}

            for i, todo in enumerate(todos):
                missing = required_fields - set(todo.keys())
                if missing:
                    return f"Todo #{i+1} missing required fields: {missing}"
                if todo.get("status") not in valid_statuses:
                    return f"Todo #{i+1} has invalid status: {todo.get('status')}. Must be one of: {valid_statuses}"

            self._save_todos(todos)

            # Return summary
            counts = {"pending": 0, "in_progress": 0, "completed": 0}
            for t in todos:
                counts[t["status"]] += 1

            return f"Updated {len(todos)} todos: {counts['in_progress']} in progress, {counts['pending']} pending, {counts['completed']} completed"

        def read_todos() -> str:
            """Read the current todo list state.

            Returns:
                JSON formatted todo list or message if empty
            """
            todos = self._load_todos()
            if not todos:
                return "No todos found."

            return json.dumps(todos, indent=2, ensure_ascii=False)

        return [
            StructuredTool.from_function(
                name="write_todos",
                func=write_todos,
                description=(
                    "Write the entire todo list at once. "
                    "Args: todos (list of dicts with content, status, activeForm)"
                ),
            ),
            StructuredTool.from_function(
                name="read_todos",
                func=read_todos,
                description="Read the current todo list state. Returns JSON.",
            ),
        ]

    def wrap_model_call(
        self,
        request: ModelRequest,
        handler,
    ) -> ModelResponse:
        """Inject system prompt with todo instructions."""
        if self.system_prompt is not None:
            current_prompt = request.system_prompt or ""
            new_prompt = (
                f"{current_prompt}\n\n{self.system_prompt}"
                if current_prompt
                else self.system_prompt
            )
            return handler(request.override(system_prompt=new_prompt))
        return handler(request)

    async def awrap_model_call(
        self,
        request: ModelRequest,
        handler,
    ) -> ModelResponse:
        """Async version of wrap_model_call."""
        if self.system_prompt is not None:
            current_prompt = request.system_prompt or ""
            new_prompt = (
                f"{current_prompt}\n\n{self.system_prompt}"
                if current_prompt
                else self.system_prompt
            )
            return await handler(request.override(system_prompt=new_prompt))
        return await handler(request)
