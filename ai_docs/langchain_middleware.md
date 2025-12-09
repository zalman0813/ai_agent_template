# LangChain v1.0 Middleware Design Principles

> Comprehensive guide to LangChain v1.0 middleware architecture for building production-ready AI agents.

## Overview

LangChain v1.0 introduces a **Middleware** abstraction layer to address the inflexibility of basic agent frameworks. Traditional agent architectures (model + prompt + tools) fall short when facing production requirements, and middleware provides a systematic approach for **Context Engineering**.

### Core Problem

Basic agent frameworks lack control over context engineering, forcing developers to abandon the framework when facing non-trivial use cases. LangChain v1.0's middleware system solves this by allowing intervention and customization at various stages of agent execution.

---

## Middleware Architecture

### Design Philosophy

LangChain middleware follows the **Web Server Middleware** design pattern:
- Multiple middleware layers can be stacked
- Each middleware can intercept and modify at specific points in the execution flow
- Requests and responses can be transformed, validated, or redirected

### Architecture Layers

```
┌─────────────────────────────────────────┐
│      Agent Execution Loop               │
├─────────────────────────────────────────┤
│ 1. before_agent (Middleware Stack)      │
│ 2. before_model (Sequential)            │
│ 3. modify_model_request (Stateless)     │
│ 4. Model Invocation                     │
│ 5. after_model (Reverse order)          │
│ 6. Tool Execution                       │
│ 7. after_agent (Middleware Stack)       │
└─────────────────────────────────────────┘
```

### Composition Patterns

1. **Sequential Composition (Middleware Stacking)**
   - Multiple middlewares execute in defined order
   - Forward path (before_* hooks): first to last
   - Backward path (after_* hooks): last to first (reversed)

2. **State Management**
   - Each middleware can access and modify shared AgentState
   - Supports custom state extensions (using Zod schemas)

3. **Execution Flow Control**
   - Supports `jump_to` mechanism for flow redirection
   - Can skip or retry execution steps

---

## Core Design Principles

### 1. Composability
- Middlewares combine like Lego blocks
- Each middleware focuses on a single responsibility
- Can add or remove middlewares freely

### 2. Flexibility
- Three different intervention points (before, modify, after)
- Each point has different purposes and capabilities
- Supports complex flow control and state management

### 3. Testability
- Middlewares can be tested independently
- Clear input/output interfaces
- Supports mocking and stubs

### 4. Production-Ready
- Built-in middleware implementations for common needs
- Supports logging, monitoring, and tracing
- Integrates with LangSmith for observability

### 5. Decoupling
- Middleware doesn't depend on specific agent implementations
- Can be reused across different agent architectures
- Supports vendor-neutral integrations

---

## The Three Main Hooks

### 1. `before_model(state)`

**Timing**: Before model invocation

**Responsibilities**:
- Update permanent state
- Execute pre-validation
- Redirect execution flow
- Make early decisions

**Capabilities**:
```python
async def before_model(self, state: AgentState) -> dict | None:
    # Can modify state
    state.messages.append(...)

    # Can return jump_to instruction
    return {"jump_to": "tools"}  # or "model" or "__end__"

    # Or return None to continue normal flow
    return None
```

**Limitations**:
- Cannot call jump_to("model") from within before_model
- Cannot access the complete request about to be sent to the model

**Common Uses**:
- PII detection and removal
- Message history summarization
- Rate limit checking
- Context length validation

---

### 2. `modify_model_request(state, request)`

**Timing**: Before model invocation (after before_model)

**Responsibilities**:
- Stateless request modification
- Adjust tool sets
- Modify system prompts
- Change message lists
- Select different models
- Adjust output formats

**Capabilities**:
```python
async def modify_model_request(
    self,
    state: AgentState,
    request: ModelRequest
) -> ModelRequest:
    # Modify tools
    request.tools = filter_relevant_tools(request.tools)

    # Modify system prompt
    request.system = "Custom system prompt..."

    # Modify messages
    request.messages = augment_messages(request.messages)

    # Note: request.model must be a BaseChatModel instance
    request.model = select_best_model(state)

    return request
```

**Important Limitations**:
- `ModelRequest.model` must be a `BaseChatModel` instance, not a string
- This hook should remain stateless
- Cannot modify AgentState

**Common Uses**:
- Dynamic tool selection
- Anthropic prompt caching
- Context-aware prompt adjustments
- Model selection logic
- Message augmentation

---

### 3. `after_model(state, response)`

**Timing**: After model returns (before tool execution)

**Responsibilities**:
- Post-validation
- Result transformation
- Human review (human-in-the-loop)
- Guardrails
- State updates

**Capabilities**:
```python
async def after_model(
    self,
    state: AgentState,
    response: ModelResponse
) -> dict | None:
    # Validate response
    if not validate_response(response):
        return {"jump_to": "__end__"}

    # Human review
    if needs_approval(response.tool_calls):
        approval = await ask_human(response)
        if not approval:
            return {"jump_to": "__end__"}

    # Update state
    state.last_model_response = response

    return None  # Continue normal flow
```

**Common Uses**:
- Tool call validation
- Human-in-the-loop workflows
- Result summarization
- Security checks
- Cost control

---

## Runnable Interface & Middleware

### Runnable Basics

`Runnable` is LangChain's foundational abstraction, representing "a unit of work that can be invoked, batched, streamed, transformed, and composed."

### Core Methods

```python
# Single input execution
result = runnable.invoke(input)
result = await runnable.ainvoke(input)

# Batch processing
results = runnable.batch([input1, input2, ...])
results = await runnable.abatch([input1, input2, ...])

# Streaming execution
for chunk in runnable.stream(input):
    print(chunk)

async for chunk in runnable.astream(input):
    print(chunk)

# Streaming with logs
async for event in runnable.astream_log(input):
    print(event)
```

### Middleware and Runnable Relationship

Middleware is essentially an interception mechanism in the Runnable execution lifecycle:

```python
class AgentRunnable(Runnable):
    def invoke(self, input: AgentInput) -> AgentOutput:
        state = AgentState(...)

        # Pre-middleware hooks
        for middleware in self.middlewares:
            await middleware.before_agent(state)

        while not is_finished(state):
            # before_model middleware
            for middleware in self.middlewares:
                result = await middleware.before_model(state)
                if result and "jump_to" in result:
                    state.next_step = result["jump_to"]
                    break

            # modify_model_request middleware
            request = prepare_model_request(state)
            for middleware in self.middlewares:
                request = await middleware.modify_model_request(state, request)

            # Execute model
            response = self.model.invoke(request)

            # after_model middleware (reverse order)
            for middleware in reversed(self.middlewares):
                result = await middleware.after_model(state, response)
                if result and "jump_to" in result:
                    state.next_step = result["jump_to"]
                    break

            # Execute tools
            if should_execute_tools(state):
                state = execute_tools(state, response)

        # Post-middleware hooks
        for middleware in reversed(self.middlewares):
            await middleware.after_agent(state)

        return state.output
```

### Runnable Composition

Middleware enables powerful Runnable composition:

```python
# Sequential composition
chain = prompt | model | output_parser

# Parallel composition
parallel_chain = {
    "branch_a": step_a,
    "branch_b": step_b
}

# Conditional composition
conditional_chain = RunnableBranch(
    (condition1, chain1),
    (condition2, chain2),
    default_chain
)

# Agent with middleware
agent = create_agent(
    model=model,
    tools=tools,
    middlewares=[
        SummarizationMiddleware(...),
        HumanInTheLoopMiddleware(...),
        AnthropicPromptCachingMiddleware(...)
    ]
)
```

---

## Callbacks System

### Relationship with Middleware

Callbacks and Middleware are two complementary observation mechanisms in LangChain:

| Aspect | Callbacks | Middleware |
|--------|-----------|-----------|
| Purpose | Monitoring and logging | Control and modification |
| Timing | When events occur | Before/after execution |
| Intervention | Cannot modify execution | Can modify and redirect |
| Use Cases | Logs, tracing, monitoring | Business logic, validation, control |

### Callbacks Architecture

```
┌──────────────────────────────────────┐
│   BaseCallbackHandler                │
├──────────────────────────────────────┤
│ Methods:                             │
│ - on_llm_start(...)                  │
│ - on_llm_end(...)                    │
│ - on_llm_error(...)                  │
│ - on_llm_new_token(...)              │
│ - on_chain_start(...)                │
│ - on_chain_end(...)                  │
│ - on_chain_error(...)                │
│ - on_tool_start(...)                 │
│ - on_tool_end(...)                   │
│ - on_tool_error(...)                 │
│ - on_agent_action(...)               │
│ - on_agent_finish(...)               │
│ - on_custom_event(...)               │
└──────────────────────────────────────┘
```

### Core Callback Events

#### LLM Related Events
```python
# Model invocation start
on_llm_start(
    serialized: dict,
    prompts: list[str],
    run_id: UUID,
    parent_run_id: UUID | None = None,
    tags: list[str] | None = None,
    metadata: dict | None = None,
    **kwargs
)

# Model invocation end
on_llm_end(
    response: LLMResult,
    run_id: UUID,
    parent_run_id: UUID | None = None,
    **kwargs
)

# New token generated (streaming)
on_llm_new_token(
    token: str,
    run_id: UUID,
    parent_run_id: UUID | None = None,
    **kwargs
)

# Model error
on_llm_error(
    error: Exception,
    run_id: UUID,
    parent_run_id: UUID | None = None,
    **kwargs
)
```

#### Agent Related Events
```python
# Agent executes action
on_agent_action(
    action: AgentAction,
    run_id: UUID,
    parent_run_id: UUID | None = None,
    **kwargs
)

# Agent finishes
on_agent_finish(
    finish: AgentFinish,
    run_id: UUID,
    parent_run_id: UUID | None = None,
    **kwargs
)
```

---

## Built-in Middleware Implementations

### 1. SummarizationMiddleware

**Purpose**: Auto-summarize long conversation history

```python
class SummarizationMiddleware(AgentMiddleware):
    """Summarize conversation history when message length exceeds threshold"""

    def __init__(
        self,
        summarizer_llm: BaseChatModel,
        token_limit: int = 4000,
        summary_window: int = 5
    ):
        self.summarizer_llm = summarizer_llm
        self.token_limit = token_limit
        self.summary_window = summary_window

    async def before_model(self, state: AgentState) -> dict | None:
        token_count = count_tokens(state.messages)

        if token_count > self.token_limit:
            recent_messages = state.messages[-self.summary_window:]
            old_messages = state.messages[:-self.summary_window]

            summary = await self.summarizer_llm.ainvoke(
                f"Summarize: {old_messages}"
            )

            state.messages = [
                SystemMessage(content=summary),
                *recent_messages
            ]

        return None
```

### 2. HumanInTheLoopMiddleware

**Purpose**: Require human approval before executing tools

```python
class HumanInTheLoopMiddleware(AgentMiddleware):
    """Require human approval before executing sensitive tools"""

    def __init__(
        self,
        sensitive_tools: list[str],
        approver: Callable
    ):
        self.sensitive_tools = sensitive_tools
        self.approver = approver

    async def after_model(
        self,
        state: AgentState,
        response: ModelResponse
    ) -> dict | None:
        for tool_call in response.tool_calls:
            if tool_call.tool_name in self.sensitive_tools:
                approved = await self.approver(
                    tool_call=tool_call,
                    state=state
                )

                if not approved:
                    return {"jump_to": "__end__"}

        return None
```

### 3. ModelCallLimitMiddleware

**Purpose**: Limit model invocation count

```python
class ModelCallLimitMiddleware(AgentMiddleware):
    """Limit total model call count"""

    def __init__(
        self,
        max_calls: int = 10,
        scope: str = "thread"
    ):
        self.max_calls = max_calls
        self.scope = scope
        self.call_count = 0

    async def before_model(self, state: AgentState) -> dict | None:
        self.call_count += 1

        if self.call_count > self.max_calls:
            return {
                "jump_to": "__end__",
                "error": f"Exceeded max model calls: {self.max_calls}"
            }

        return None
```

### 4. PIIMiddleware

**Purpose**: Detect and remove personally identifiable information

```python
class PIIMiddleware(AgentMiddleware):
    """Detect and remove PII from messages"""

    async def before_model(self, state: AgentState) -> dict | None:
        for i, message in enumerate(state.messages):
            cleaned_content = self.redact_pii(message.content)
            if cleaned_content != message.content:
                state.messages[i].content = cleaned_content

        return None

    def redact_pii(self, text: str) -> str:
        text = re.sub(r'\b\d{3}-\d{2}-\d{4}\b', '[SSN REDACTED]', text)
        text = re.sub(r'\b\d{16}\b', '[CARD REDACTED]', text)
        text = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[EMAIL REDACTED]', text)
        return text
```

### 5. AnthropicPromptCachingMiddleware

**Purpose**: Leverage Anthropic's prompt caching feature

```python
class AnthropicPromptCachingMiddleware(AgentMiddleware):
    """Implement prompt caching for Anthropic models"""

    async def modify_model_request(
        self,
        state: AgentState,
        request: ModelRequest
    ) -> ModelRequest:
        if not isinstance(request.model, ChatAnthropic):
            return request

        if len(request.messages) > 3:
            request.model_kwargs["system"] = {
                "type": "text",
                "text": request.system,
                "cache_control": {"type": "ephemeral"}
            }

        return request
```

---

## Code Examples

### Example 1: Basic Middleware Creation

```python
from langchain.agents import AgentMiddleware, AgentState, ModelRequest, ModelResponse
from langchain_core.language_models import BaseChatModel
from typing import Optional

class LoggingMiddleware(AgentMiddleware):
    """Log all agent execution steps"""

    async def before_agent(self, state: AgentState) -> None:
        print(f"[AGENT START] Input: {state.input}")

    async def before_model(self, state: AgentState) -> Optional[dict]:
        print(f"[BEFORE MODEL] Messages: {len(state.messages)}")
        return None

    async def modify_model_request(
        self,
        state: AgentState,
        request: ModelRequest
    ) -> ModelRequest:
        print(f"[MODIFY REQUEST] Tools: {[t.name for t in request.tools]}")
        return request

    async def after_model(
        self,
        state: AgentState,
        response: ModelResponse
    ) -> Optional[dict]:
        print(f"[AFTER MODEL] Tool calls: {response.tool_calls}")
        return None

    async def after_agent(self, state: AgentState) -> None:
        print(f"[AGENT END] Output: {state.output}")
```

### Example 2: Composing Multiple Middlewares

```python
from langchain.agents import create_agent
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool

@tool
def get_weather(location: str) -> str:
    """Get weather information"""
    return f"Sunny in {location}, 25°C"

@tool
def search_web(query: str) -> str:
    """Search the web"""
    return f"Search results for '{query}'..."

model = ChatOpenAI(model="gpt-4")

agent = create_agent(
    model=model,
    tools=[get_weather, search_web],
    middlewares=[
        LoggingMiddleware(),
        ModelCallLimitMiddleware(max_calls=10),
        SummarizationMiddleware(
            summarizer_llm=model,
            token_limit=4000
        ),
        HumanInTheLoopMiddleware(
            sensitive_tools=["delete_file", "transfer_funds"],
            approver=ask_human_for_approval
        ),
        PIIMiddleware()
    ]
)

response = await agent.ainvoke({
    "input": "What's the weather in Beijing today?"
})
```

---

## Best Practices

### 1. Single Responsibility Principle

Each middleware should do only one thing:

```python
# Good
class RateLimitMiddleware(AgentMiddleware):
    """Only handles rate limiting"""
    async def before_model(self, state: AgentState) -> Optional[dict]:
        if self.check_rate_limit(state):
            return None
        return {"jump_to": "__end__"}

# Bad
class DoEverythingMiddleware(AgentMiddleware):
    """Tries to handle everything - too many responsibilities"""
    pass
```

### 2. Stateless modify_model_request

This hook should be stateless, only for transforming requests:

```python
# Good
async def modify_model_request(
    self,
    state: AgentState,
    request: ModelRequest
) -> ModelRequest:
    request.tools = filter_tools(request.tools)
    return request

# Bad - modifying state (should be done in before_model)
async def modify_model_request(
    self,
    state: AgentState,
    request: ModelRequest
) -> ModelRequest:
    state.modified_count += 1  # Don't do this
    request.tools = filter_tools(request.tools)
    return request
```

### 3. Explicit Error Handling

```python
async def before_model(self, state: AgentState) -> Optional[dict]:
    try:
        result = await self.check_something(state)
    except Exception as e:
        logger.error(f"Middleware error: {e}")
        return None

    if not result:
        return {"jump_to": "__end__", "error": "Check failed"}

    return None
```

### 4. Composition Order Matters

```python
middlewares = [
    # 1. Validation and checks first
    ValidationMiddleware(),

    # 2. Security checks
    SecurityMiddleware(),

    # 3. Optimizations
    OptimizationMiddleware(),

    # 4. Monitoring last
    MonitoringMiddleware()
]
```

### 5. Use Together with Callbacks

```python
class CustomCallback(BaseCallbackHandler):
    """For monitoring"""

    def on_agent_finish(self, finish: AgentFinish, **kwargs):
        print(f"Agent finished: {finish}")

result = agent.invoke(
    input,
    config={
        "callbacks": [CustomCallback()],
    }
)
```

---

## Key Takeaways

1. **Middleware is composable**: Stack like Lego blocks
2. **Three hooks, three responsibilities**: Each hook has a specific purpose
3. **State management matters**: Use AgentState appropriately
4. **Execution order is predictable**: before forward, after reversed
5. **Complements Callbacks**: Middleware controls, Callbacks monitor

---

**Document generated**: November 30, 2025
**Applicable version**: LangChain v1.0+
**Status**: Based on latest official documentation (2024-2025)
