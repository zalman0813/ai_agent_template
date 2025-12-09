# AI Docs

> Resources to fetch and load into ai_docs/*.md at runtime

## LangChain v1.0 Middleware
- https://blog.langchain.com/agent-middleware/
- https://reference.langchain.com/python/langchain/middleware/
- https://docs.langchain.com/oss/python/langchain/middleware/custom
- https://reference.langchain.com/python/langchain_core/runnables/
- https://reference.langchain.com/python/langchain_core/callbacks/
- https://blog.langchain.com/langchain-langgraph-1dot0/
- https://colinmcnamara.com/blog/langchain-middleware-v1-alpha-guide
- https://codecut.ai/langchain-1-0-middleware-production-agents/
- https://skywork.ai/blog/ai-agent/best-practices-langchain-1-0-production-ready-llm-apps/

## LangSmith Observability

### 官方文檔
- https://docs.smith.langchain.com/observability/how_to_guides/annotate_code
- https://docs.smith.langchain.com/observability/how_to_guides/trace_with_langchain
- https://docs.smith.langchain.com/observability/concepts
- https://docs.smith.langchain.com/observability/how_to_guides/add_metadata_tags
- https://docs.smith.langchain.com/observability/how_to_guides/sample_traces
- https://docs.smith.langchain.com/observability/how_to_guides/mask_inputs_outputs
- https://docs.smith.langchain.com/evaluation/concepts#feedback

### SDK 參考
- https://docs.smith.langchain.com/reference/python/
- https://docs.smith.langchain.com/reference/python/run_helpers/langsmith.run_helpers.traceable
- https://docs.smith.langchain.com/reference/python/run_trees/langsmith.run_trees.RunTree

### 進階資源
- https://github.com/langchain-ai/langsmith-cookbook
- https://github.com/langchain-ai/langsmith-sdk

## Deep Agents & Planning Architecture

### LangChain Deep Agents (Official)
- https://blog.langchain.com/deep-agents/
- https://docs.langchain.com/oss/python/deepagents/overview
- https://docs.langchain.com/oss/python/deepagents/middleware
- https://docs.langchain.com/oss/python/deepagents/quickstart
- https://docs.langchain.com/oss/python/deepagents/subagents
- https://docs.langchain.com/oss/python/deepagents/backends
- https://docs.langchain.com/oss/python/deepagents/human-in-the-loop
- https://docs.langchain.com/oss/python/deepagents/long-term-memory
- https://github.com/langchain-ai/deepagents
- https://github.com/langchain-ai/deepagents-quickstarts

### Claude Code Architecture
- https://docs.anthropic.com/en/docs/claude-code/overview
- https://docs.anthropic.com/en/docs/claude-code/sub-agents
- https://claudelog.com/faqs/what-is-todo-list-in-claude-code/

### Deep Research & Agent Design Patterns
- https://manus.im/blog/Context-Engineering-for-AI-Agents-Lessons-from-Building-Manus
- https://metr.org/blog/2025-03-19-measuring-ai-ability-to-complete-long-tasks/

### Key Concepts
Deep agents are characterized by four components:
1. **Detailed system prompt** - Complex instructions with examples
2. **Planning tool** - TodoList for tracking multi-step tasks
3. **Sub-agents** - Context isolation for complex subtasks
4. **File system** - Persistent storage for context management

## LangChain Tool Error Handling

### Official Documentation
- https://docs.langchain.com/oss/python/langchain/tools
- https://docs.langchain.com/oss/python/langchain/middleware/built-in#tool-retry
- https://docs.langchain.com/oss/python/langchain/middleware/custom#wrap-style-hooks
- https://reference.langchain.com/python/langchain/middleware/#langchain.agents.middleware.ToolRetryMiddleware

### Pydantic Schema Validation
- https://docs.langchain.com/oss/python/langchain/tools#advanced-schema-definition

### Key Concepts
- **ToolRetryMiddleware**: Built-in middleware for automatic retry with exponential backoff
- **wrap_tool_call**: Custom middleware hook for intercepting tool execution
- **args_schema**: Pydantic model for strict input validation
- **handle_tool_error**: Tool-level error handling configuration
