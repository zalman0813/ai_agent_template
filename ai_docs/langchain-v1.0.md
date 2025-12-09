# LangChain v1.0 Documentation

> Reference documentation for AI agents working with LangChain v1.0

## Important Changes in v1.0

LangChain v1.0 (released 2025) introduced breaking changes:

| Old (pre-1.0) | New (v1.0) |
|---------------|------------|
| `langgraph.prebuilt.create_react_agent` | `langchain.agents.create_agent` |
| Manual tool binding | Automatic via `create_agent` |
| Custom state management | Middleware system |

## Core Imports

```python
# Agent creation
from langchain.agents import create_agent

# Model initialization
from langchain.chat_models import init_chat_model

# Tool definition
from langchain_core.tools import tool

# Anthropic model
from langchain_anthropic import ChatAnthropic

# Middleware
from deepagents.middleware.subagents import SubAgentMiddleware
from langchain.agents.middleware.todo import TodoListMiddleware

# Search tools
from langchain_tavily import TavilySearch
```

## Creating Agents

### Basic Agent

```python
from langchain.agents import create_agent
from langchain.chat_models import init_chat_model
from langchain_core.tools import tool

@tool
def my_tool(input: str) -> str:
    """Tool description that the model will see."""
    return f"Processed: {input}"

model = init_chat_model(
    "claude-sonnet-4-5-20250929",
    model_provider="anthropic",
    temperature=0.7
)

agent = create_agent(
    model=model,
    tools=[my_tool],
    system_prompt="You are a helpful assistant."
)

# Invoke
result = agent.invoke({
    "messages": [{"role": "user", "content": "Hello"}]
})
print(result["messages"][-1].content)
```

### Agent with Middleware

```python
from langchain.agents import create_agent
from langchain.agents.middleware.todo import TodoListMiddleware

agent = create_agent(
    model=model,
    tools=[my_tool],
    system_prompt="...",
    middleware=[
        TodoListMiddleware()
    ]
)
```

## Defining Tools

### Using @tool Decorator (Recommended)

```python
from langchain_core.tools import tool

@tool
def simple_tool(input: str) -> str:
    """Description of what this tool does."""
    return f"Result: {input}"

@tool
def tool_with_params(
    query: str,
    limit: int = 10,
    filter_type: str = None
) -> str:
    """
    Search with parameters.

    Args:
        query: Search query string
        limit: Max results (default: 10)
        filter_type: Optional filter
    """
    return f"Found {limit} results for: {query}"
```

### Using Pydantic for Complex Parameters

```python
from langchain_core.tools import tool
from pydantic import BaseModel, Field

class EmailInput(BaseModel):
    recipient: str = Field(description="Email address")
    subject: str = Field(description="Email subject")
    body: str = Field(description="Email content")

@tool
def send_email(email: EmailInput) -> str:
    """Send an email to recipient."""
    return f"Sent to {email.recipient}"
```

## Multi-Agent Systems

### Using SubAgentMiddleware

```python
from langchain.agents import create_agent
from langchain.chat_models import init_chat_model
from deepagents.middleware.subagents import SubAgentMiddleware
from langchain_tavily import TavilySearch

model = init_chat_model(
    "claude-sonnet-4-5-20250929",
    model_provider="anthropic"
)

search_tool = TavilySearch(max_results=5)

primary_agent = create_agent(
    model=model,
    tools=[my_tool],
    system_prompt="""You are an assistant with subagents.
Delegate web searches to web_search_agent.""",
    middleware=[
        SubAgentMiddleware(
            default_model="claude-sonnet-4-5-20250929",
            subagents=[
                {
                    "name": "web_search_agent",
                    "description": "Search the web for information",
                    "system_prompt": "You are a research specialist.",
                    "tools": [search_tool],
                }
            ]
        )
    ]
)
```

### Subagent Definition Schema

```python
{
    "name": str,           # Unique identifier for the subagent
    "description": str,    # When to use this subagent (for delegation)
    "system_prompt": str,  # Instructions for the subagent
    "tools": list,         # Tools available to the subagent
    "model": str,          # Optional: override model (default: parent's model)
}
```

## Model Initialization

### Using init_chat_model (Recommended)

```python
from langchain.chat_models import init_chat_model

# Claude Sonnet 4.5
model = init_chat_model(
    "claude-sonnet-4-5-20250929",
    model_provider="anthropic",
    temperature=0.7,
    max_tokens=2000
)

# OpenAI GPT-4
model = init_chat_model(
    "gpt-4-turbo",
    model_provider="openai"
)
```

### Direct Instantiation

```python
from langchain_anthropic import ChatAnthropic

model = ChatAnthropic(
    model="claude-sonnet-4-5-20250929",
    temperature=0.7,
    max_tokens=2000
)
```

## Web Search with Tavily

### Installation

```bash
uv add langchain-tavily
```

### Usage

```python
from langchain_tavily import TavilySearch

# Basic search
search = TavilySearch(max_results=5)

# With options
search = TavilySearch(
    max_results=5,
    topic="general",  # or "news"
    # include_answer=True,
    # search_depth="advanced"
)
```

### Environment Variable

```env
TAVILY_API_KEY=your-api-key
```

Get free API key (1000 searches/month): https://tavily.com

## Agent Invocation

### Basic Invoke

```python
result = agent.invoke({
    "messages": [
        {"role": "user", "content": "Your message here"}
    ]
})

# Get response
response = result["messages"][-1].content
```

### With History

```python
result = agent.invoke({
    "messages": [
        {"role": "user", "content": "My name is Alice"},
        {"role": "assistant", "content": "Hello Alice!"},
        {"role": "user", "content": "What's my name?"}
    ]
})
```

## Available Middleware

| Middleware | Purpose |
|------------|---------|
| `TodoListMiddleware` | Track and manage todos |
| `SubAgentMiddleware` | Enable subagent delegation |

**Note**: Cannot use `middleware` and `state_schema` parameters together (known limitation).

## Best Practices

1. **Tool Docstrings**: Always write clear docstrings - they become the tool description for the model
2. **Type Hints**: Always use type hints for tool parameters
3. **Subagent Context**: Each subagent has isolated context (good for security)
4. **Model Selection**: Use `init_chat_model` for flexibility across providers

## Claude Model IDs

| Model | ID |
|-------|-----|
| Claude Sonnet 4.5 | `claude-sonnet-4-5-20250929` |
| Claude Opus 4.5 | `claude-opus-4-5-20251101` |
| Claude Haiku 3.5 | `claude-3-5-haiku-20241022` |

## Requirements

- Python >= 3.10
- langchain >= 1.0.0
- langchain-anthropic >= 0.3.0
- langchain-tavily >= 0.1.0 (for web search)

## Package Installation with uv

```bash
# Install all dependencies
uv add langchain langchain-anthropic langchain-tavily python-dotenv

# Or with pyproject.toml
uv sync
```

## LangSmith 可觀測性

詳細的 LangSmith 追蹤與 observability 指南請參考：
- [LangSmith 可觀測性指南](./langsmith-observability.md)

---

## Sources

### 官方文檔
- [LangChain Documentation](https://python.langchain.com/docs/)
- [LangChain v1.0 Migration Guide](https://python.langchain.com/docs/versions/v0_3/)
- [LangSmith Documentation](https://docs.smith.langchain.com/)
- [LangSmith Observability](https://docs.smith.langchain.com/observability/)
- [LangSmith Python SDK](https://docs.smith.langchain.com/reference/python/)

### API 參考
- [LangChain Core Tools](https://python.langchain.com/docs/modules/tools/)
- [LangChain Chat Models](https://python.langchain.com/docs/integrations/chat/)
- [LangChain Anthropic](https://python.langchain.com/docs/integrations/chat/anthropic/)
- [Tavily Search](https://python.langchain.com/docs/integrations/tools/tavily_search/)

### 進階資源
- [LangSmith Cookbook](https://github.com/langchain-ai/langsmith-cookbook)
- [LangChain Templates](https://github.com/langchain-ai/langchain/tree/master/templates)
- [Anthropic Claude Models](https://docs.anthropic.com/en/docs/about-claude/models)
