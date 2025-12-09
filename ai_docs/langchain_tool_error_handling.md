# LangChain Tool Error Handling

> Official documentation for handling tool execution errors in LangChain v1.0 agents.

## Overview

LangChain provides multiple mechanisms for handling tool execution errors:

1. **Tool-level validation** - Pydantic schemas with `args_schema`
2. **ToolRetryMiddleware** - Built-in retry with exponential backoff
3. **Custom middleware** - `wrap_tool_call` hook for custom error handling
4. **Tool-level error handling** - `handle_tool_error` parameter

---

## 1. Pydantic Schema Validation (args_schema)

Define strict input validation with Pydantic models:

```python
from pydantic import BaseModel, Field
from typing import Literal
from langchain.tools import tool

class WeatherInput(BaseModel):
    """Input for weather queries."""
    location: str = Field(description="City name or coordinates")
    units: Literal["celsius", "fahrenheit"] = Field(
        default="celsius",
        description="Temperature unit preference"
    )

@tool(args_schema=WeatherInput)
def get_weather(location: str, units: str = "celsius") -> str:
    """Get current weather."""
    return f"Weather in {location}: 22 degrees {units}"
```

**Benefits:**
- Automatic validation before tool execution
- Clear error messages with field names and expected values
- Enum validation ensures only valid values are accepted

**Source:** https://docs.langchain.com/oss/python/langchain/tools#advanced-schema-definition

---

## 2. ToolRetryMiddleware (Built-in)

Automatically retry failed tool calls with configurable exponential backoff.

```python
from langchain.agents import create_agent
from langchain.agents.middleware import ToolRetryMiddleware

agent = create_agent(
    model="gpt-4o",
    tools=[search_tool, database_tool],
    middleware=[
        ToolRetryMiddleware(
            max_retries=3,
            backoff_factor=2.0,
            initial_delay=1.0,
            max_delay=60.0,
            jitter=True,
            tools=["api_tool"],  # Optional: specific tools only
            retry_on=(ConnectionError, TimeoutError),  # Optional: specific exceptions
            on_failure="return_message",  # or "raise"
        ),
    ],
)
```

### Configuration Options

| Parameter | Default | Description |
|-----------|---------|-------------|
| `max_retries` | 2 | Maximum retry attempts after initial call |
| `tools` | None | List of tools to apply retry (None = all tools) |
| `retry_on` | (Exception,) | Exception types to retry, or callable |
| `on_failure` | "return_message" | Behavior when retries exhausted |
| `backoff_factor` | 2.0 | Multiplier for exponential backoff |
| `initial_delay` | 1.0 | Initial delay in seconds |
| `max_delay` | 60.0 | Maximum delay cap |
| `jitter` | True | Add random ±25% variation |

### on_failure Options

- `"return_message"` - Return ToolMessage with error (allows LLM to handle)
- `"raise"` - Re-raise exception (stops agent)
- Custom callable - Function returning error message string

**Source:** https://docs.langchain.com/oss/python/langchain/middleware/built-in#tool-retry

---

## 3. Custom Middleware with wrap_tool_call

Create custom error handling with the `wrap_tool_call` hook:

```python
from langchain.agents.middleware import wrap_tool_call
from langchain.tools.tool_node import ToolCallRequest
from langchain.messages import ToolMessage
from langgraph.types import Command
from typing import Callable

@wrap_tool_call
def monitor_tool(
    request: ToolCallRequest,
    handler: Callable[[ToolCallRequest], ToolMessage | Command],
) -> ToolMessage | Command:
    print(f"Executing tool: {request.tool_call['name']}")
    print(f"Arguments: {request.tool_call['args']}")
    try:
        result = handler(request)
        print(f"Tool completed successfully")
        return result
    except Exception as e:
        print(f"Tool failed: {e}")
        # Return error message for AI to self-correct
        return ToolMessage(
            content=f"Tool failed: {e}. Please fix and retry.",
            tool_call_id=request.tool_call_id,
            name=request.tool_call['name'],
            status="error",
        )
```

### Class-based Middleware

```python
from langchain.agents.middleware import AgentMiddleware

class ErrorHandlingMiddleware(AgentMiddleware):
    def __init__(self, max_retries: int = 3, verbose: bool = False):
        super().__init__()
        self.max_retries = max_retries
        self.verbose = verbose
        self._retry_counts = {}

    def wrap_tool_call(self, request, execute):
        try:
            result = execute(request)
            return result
        except Exception as e:
            if self.verbose:
                print(f"[Error] Tool '{request.tool}': {e}")
            return ToolMessage(
                content=f"Error: {e}. Please correct and try again.",
                tool_call_id=request.tool_call_id,
                name=request.tool,
                status="error",
            )

    async def awrap_tool_call(self, request, execute):
        # Async version
        try:
            return await execute(request)
        except Exception as e:
            return ToolMessage(
                content=f"Error: {e}",
                tool_call_id=request.tool_call_id,
                name=request.tool,
                status="error",
            )
```

**Source:** https://docs.langchain.com/oss/python/langchain/middleware/custom#wrap-style-hooks

---

## 4. Tool-level handle_tool_error

Configure error handling directly on tools:

```python
from langchain_core.tools import StructuredTool

def handle_error(error: Exception) -> str:
    return f"Tool error: {error}. Please try with different parameters."

tool = StructuredTool.from_function(
    name="my_tool",
    func=my_function,
    description="Tool description",
    args_schema=MyInputSchema,
    handle_tool_error=handle_error,  # or True for default, or string
)
```

### handle_tool_error Options

- `True` - Use default error message
- `str` - Use this string as error message
- `Callable[[Exception], str]` - Custom error formatting function

---

## AI Self-Correction Pattern

The key to enabling AI self-correction is returning clear error messages as `ToolMessage`:

```python
# Error message structure for AI self-correction
ToolMessage(
    content="Field 'priority': Invalid value 'urgent'. Must be one of: 'low', 'medium', 'high'.",
    tool_call_id=request.tool_call_id,
    name=request.tool,
    status="error",  # Mark as error
)
```

The AI receives this as an observation and can:
1. Analyze the error message
2. Understand what went wrong
3. Retry with corrected parameters

### System Prompt for Self-Correction

Add guidance in system prompt:

```python
system_prompt = """
When tool calls fail:
- READ the error message carefully
- FIX the issue based on the error
- TRY AGAIN with corrected parameters
- If errors persist, ask the user for help
"""
```

---

## Execution Order

When using multiple middleware:

```
before_* hooks: First → Last
wrap_* hooks: Nested (first wraps all others)
after_* hooks: Last → First (reverse)
```

Example:
```python
middleware=[middleware1, middleware2, middleware3]
# wrap_tool_call execution:
# middleware1.wrap_tool_call → middleware2.wrap_tool_call → middleware3.wrap_tool_call → tool
```

---

## Best Practices

1. **Use Pydantic schemas** for input validation with clear field descriptions
2. **Return error messages** (not raise) to allow AI self-correction
3. **Include retry limits** to prevent infinite loops
4. **Log errors** for debugging with verbose mode
5. **Add specific guidance** in error messages about how to fix

---

## Official Documentation Links

- Tools: https://docs.langchain.com/oss/python/langchain/tools
- ToolRetryMiddleware: https://docs.langchain.com/oss/python/langchain/middleware/built-in#tool-retry
- Custom Middleware: https://docs.langchain.com/oss/python/langchain/middleware/custom
- Middleware API Reference: https://reference.langchain.com/python/langchain/middleware/
