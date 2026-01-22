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

## Agent Skills (Open Standard)

### Official Specification
- https://agentskills.io/home
- https://agentskills.io/specification
- https://agentskills.io/what-are-skills
- https://agentskills.io/integrate-skills

### Anthropic Implementation
- https://github.com/anthropics/skills
- https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills
- https://docs.anthropic.com/en/docs/agents-and-tools/agent-skills/overview

### GitHub Specification
- https://github.com/agentskills/agentskills
- https://github.com/agentskills/agentskills/tree/main/skills-ref

### Key Concepts
- **Open Standard**: October 2025 by Anthropic, December 2025 published at agentskills.io
- **SKILL.md files**: Markdown-based skill definitions with YAML frontmatter
- **Supported Platforms**: Claude Code, Claude.ai, GitHub, Cursor, VS Code, OpenAI Codex, Gemini CLI, Goose, Letta, OpenCode, Amp, Factory

## LangChain Deep Agents SkillsMiddleware

### Official Documentation
- https://docs.langchain.com/oss/python/deepagents/middleware
- https://reference.langchain.com/python/deepagents/middleware/skills/
- https://www.blog.langchain.com/using-skills-with-deep-agents/

### GitHub
- https://github.com/langchain-ai/deepagents
- https://github.com/langchain-ai/deepagents-quickstarts

### Key Concepts
- **SkillsMiddleware**: Middleware for loading and exposing agent skills to the system prompt
- **Progressive disclosure**: Only YAML frontmatter loads by default; full SKILL.md read on demand
- **Package**: `deepagents.middleware.skills.SkillsMiddleware`
- **Introduced**: November 2025 (as part of Deep Agents framework)

## DeepAgents CLI vs SDK Architecture

### Comprehensive Documentation (Split into 8 Parts)
- **Index**: `deepagents-architecture/INDEX.md` - Start here for navigation
- **Original Single File**: `deepagents-cli-vs-sdk-architecture.md` (5,685 lines)

### Document Structure
The documentation is split into 8 parts for easier reading (~600-800 lines each):

1. **[Part 1: Overview](deepagents-architecture/part1-overview.md)** - Sections 1-3
   - Executive Summary, CLI vs SDK Overview, Architecture Comparison

2. **[Part 2: Core Concepts](deepagents-architecture/part2-core-concepts.md)** - Sections 4-5
   - Core Concepts, Backend Implementations Deep Dive (5 backend types)

3. **[Part 3: Middleware & Execution](deepagents-architecture/part3-middleware-execution.md)** - Sections 6-7
   - Middleware Comparison, Execution Mechanisms (bash vs execute)

4. **[Part 4: Skills & Decision](deepagents-architecture/part4-skills-decision.md)** - Sections 8-9
   - Skills System, Decision Framework (when to use CLI vs SDK)

5. **[Part 5: Implementation](deepagents-architecture/part5-implementation.md)** - Section 10
   - 7 Complete Implementation Patterns (minimal to full-featured)

6. **[Part 6: Comparison & Patterns](deepagents-architecture/part6-comparison-patterns.md)** - Sections 11-12
   - Comparison Tables, Common Patterns and Anti-Patterns

7. **[Part 7: Migration & Troubleshooting](deepagents-architecture/part7-migration-troubleshooting.md)** - Sections 13-14
   - Migration Guide, Troubleshooting (common issues and solutions)

8. **[Part 8: Reference](deepagents-architecture/part8-reference.md)** - Sections 15-17
   - FAQ (30+ questions), Glossary, Additional Resources

### Quick Navigation by Use Case
- **Learning DeepAgents?** → Start with [Part 1](deepagents-architecture/part1-overview.md) and [Part 4](deepagents-architecture/part4-skills-decision.md)
- **Building First Agent?** → [Part 5: Pattern 3](deepagents-architecture/part5-implementation.md) (Docker Execution)
- **Production Deployment?** → [Part 5: Pattern 5](deepagents-architecture/part5-implementation.md) (Full-Featured)
- **Troubleshooting?** → [Part 7](deepagents-architecture/part7-migration-troubleshooting.md) and [Part 8 FAQ](deepagents-architecture/part8-reference.md)
- **Migration CLI→SDK?** → [Part 7: Section 13](deepagents-architecture/part7-migration-troubleshooting.md)

### Key Topics Covered
- **Architecture Comparison**: CLI vs SDK execution models and data flows
- **Backend Implementations**: StateBackend, FilesystemBackend, DockerBackend, RemoteBackend, CompositeBackend
- **Middleware Deep Dive**: FilesystemMiddleware, SkillsMiddleware, SubAgentMiddleware
- **Execution Mechanisms**: Shell vs execute, working directories, path resolution
- **Skills System**: Discovery, progressive disclosure, implementation patterns
- **Decision Framework**: When to use CLI vs SDK
- **Implementation Patterns**: From minimal to full-featured setups (7 patterns)
- **Migration Guide**: CLI to SDK and vice versa
- **Troubleshooting**: Common issues and solutions
- **FAQ**: 30+ frequently asked questions

### Key Concepts
- **CLI Approach**: Direct host execution (Claude Code, bash tool)
- **SDK Approach**: Sandboxed execution with pluggable backends
- **CompositeBackend**: Path-based routing for performance optimization
- **Backend Factory Pattern**: Lambda factories for runtime-dependent backends
- **Progressive Disclosure**: Skills loaded incrementally (Level 1/2/3)
- **Hybrid Approach**: Develop with CLI, deploy with SDK