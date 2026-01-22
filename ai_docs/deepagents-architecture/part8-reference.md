# DeepAgents CLI vs SDK Architecture - Part 8: Reference

> **Navigation**: [⬅️ Part 7: Migration & Troubleshooting](part7-migration-troubleshooting.md) | [Index](INDEX.md)

**Sections**: 15-17 | FAQ, Glossary, Additional Resources

---

## 15. FAQ

Frequently asked questions about DeepAgents CLI vs SDK.

### 15.1 General Questions

**Q: When should I use CLI vs SDK?**

A: Use CLI for:
- Personal automation
- Development/learning
- Rapid prototyping
- Trusted environments

Use SDK for:
- Production deployments
- Multi-user applications
- Security-critical systems
- Custom functionality needs

**Q: Can I mix CLI and SDK approaches?**

A: Yes! You can:
- Develop with CLI, deploy with SDK
- Use SDK with ShellMiddleware for CLI-like behavior
- Use CLI for some tasks, SDK for others

**Q: Is the SDK more secure than CLI?**

A: The SDK *can* be more secure when configured with:
- DockerBackend for sandboxing
- Resource limits
- Proper isolation

But the SDK itself doesn't guarantee security - it depends on your configuration.

**Q: What's the performance difference?**

A: CLI is slightly faster (~10-50ms less overhead per operation) because it has fewer layers. However, SDK with CompositeBackend can achieve similar performance for file operations while maintaining sandboxing for execution.

### 15.2 Backend Questions

**Q: Can I use multiple backends simultaneously?**

A: Yes, with CompositeBackend:

```python
composite = CompositeBackend(
    default=DockerBackend(...),
    routes={
        "/local/": FilesystemBackend(...),
        "/remote/": RemoteBackend(...),
    }
)
```

**Q: Do I need Docker to use the SDK?**

A: No! You can use:
- StateBackend only (no execution)
- FilesystemBackend (file operations, no execution)
- RemoteBackend (execute on remote server)
- Custom backend (any execution environment)

**Q: Can DockerBackend run Windows containers?**

A: DockerBackend supports whatever Docker supports on your platform. On Windows, you can run both Windows and Linux containers depending on Docker configuration.

**Q: How do I share data between backends?**

A: Use volume mounts or shared storage:

```python
# Shared volume approach
docker = DockerBackend(
    volumes={
        "/shared-data": "/shared-data",  # Both host and container see it
    }
)
```

**Q: Can I use DockerBackend without docker-py?**

A: DockerBackend requires the Docker Python SDK (`docker` package) and a running Docker daemon.

### 15.3 Middleware Questions

**Q: What order should middleware be in?**

A: General pattern:
1. State modification (TodoList, Skills)
2. Tool generation (Filesystem)
3. Delegation (SubAgent)
4. Context management (Summarization)
5. Protocol fixes (Caching, ToolCallPatch)

**Q: Can I create custom middleware?**

A: Yes! Implement the middleware protocol:

```python
class CustomMiddleware:
    def before_model(self, state):
        # Modify state before model call
        return state

    def after_model(self, state):
        # Modify state after model call
        return state

    def modify_tools(self, tools):
        # Add/modify tools
        return tools
```

**Q: Why do I need FilesystemMiddleware if I have a backend?**

A: FilesystemMiddleware:
- Generates tools from backend capabilities
- Routes tool calls to backend
- Provides the execute() tool

Without it, the agent won't have file/execution tools.

**Q: Can SkillsMiddleware work with multiple skill directories?**

A: Yes:

```python
SkillsMiddleware(
    sources=["/skills/", "/custom-skills/", "/team-skills/"]
)
```

### 15.4 Skills Questions

**Q: Can skills be in any programming language?**

A: Yes! Skills are just executable scripts. Common languages:
- Python
- Bash
- JavaScript/Node.js
- Any language available in your backend environment

**Q: How many skills can I have?**

A: Technically unlimited, but consider token costs:
- Each skill: ~30 tokens (name + description)
- 100 skills: ~3000 tokens
- Use selective loading or categories for many skills

**Q: Can skills call other skills?**

A: Yes, skills can execute other skill scripts:

```bash
# In skill-a/scripts/main.py
import subprocess
subprocess.run(["python", "/skills/skill-b/scripts/helper.py"])
```

**Q: Can I use skills from a remote repository?**

A: Yes, but you need to download them first:

```python
# Download skills at startup
import git
git.Repo.clone_from("https://github.com/org/skills", "./skills")

# Then use SkillsMiddleware
SkillsMiddleware(sources=[" ./skills/"])
```

**Q: Do skills work with CLI?**

A: Skills work best with SDK (automatic discovery). For CLI, you need to manually document skills in the system prompt.

### 15.5 Execution Questions

**Q: Can I run GUI applications in DockerBackend?**

A: DockerBackend is designed for headless execution. For GUI apps, you need X11 forwarding:

```python
docker = DockerBackend(
    environment={"DISPLAY": ":0"},
    volumes={"/tmp/.X11-unix": "/tmp/.X11-unix"},
)
```

**Q: How do I handle long-running processes?**

A: Use background execution:

```python
# Start process in background
execute("python long_task.py > /workspace/output.log 2>&1 &")

# Check status later
execute("ps aux | grep long_task.py")
```

**Q: Can I execute commands with sudo?**

A: In DockerBackend, you can configure the container user:

```python
docker = DockerBackend(
    user="root",  # Run as root in container
)
```

For RemoteBackend, the remote user needs sudo permissions.

**Q: How do I handle interactive commands?**

A: Avoid interactive commands. Use non-interactive alternatives:

```bash
# Interactive (avoid)
execute("apt-get install python3")

# Non-interactive (use this)
execute("apt-get install -y python3")
```

### 15.6 Debugging Questions

**Q: How do I debug what the agent is doing?**

A: Enable logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Logs will show:
# - Tool calls
# - Backend operations
# - Middleware execution
```

**Q: How do I see what's in the Docker container?**

A: Use docker exec:

```bash
# Get a shell in container
docker exec -it agent-sandbox bash

# Run commands
ls /workspace/
cat /workspace/file.txt
```

**Q: Why is my agent making unexpected tool calls?**

A: Check:
1. System prompt - is it clear about tool usage?
2. Tool descriptions - are they accurate?
3. Available tools - does agent have the right tools?
4. Context - is there enough context for the agent?

**Q: How do I test my backend without the agent?**

A: Test backend directly:

```python
backend = DockerBackend(...)

# Test operations
print(backend.execute("echo 'Hello'"))
print(backend.read_file("/workspace/test.txt"))
print(backend.ls("/workspace/"))
```

---

## 16. Glossary

### A

**Agent**
An AI system (typically powered by a large language model) that can take actions through tool calls. In DeepAgents, agents are built using LangChain and execute in configurable environments.

**Agent Skills**
Lightweight, file-based extensions that provide specialized capabilities to agents through structured documentation (SKILL.md) and executable scripts.

**AnthropicPromptCachingMiddleware**
Middleware that enables prompt caching for Anthropic Claude models, reducing token costs and latency for repeated content.

### B

**Backend**
Defines where and how agent operations execute. Examples: StateBackend, FilesystemBackend, DockerBackend, RemoteBackend, CompositeBackend.

**Backend Protocol**
Interface specification that backends must implement. Defines methods like `read_file()`, `write_file()`, `execute()`, etc.

**bash Tool**
CLI tool that executes shell commands directly on the host system. Used in CLI approaches like Claude Code.

### C

**CLI Approach**
Building AI agents using command-line interfaces where the agent sends bash commands directly to the host system. Example: Claude Code CLI.

**Claude Code**
Anthropic's official CLI tool for Claude, providing a command-line interface for AI-powered coding assistance.

**CompositeBackend**
Backend that routes operations to different backends based on path prefixes. Enables mixing fast host reads with sandboxed execution.

**Container**
Isolated execution environment provided by Docker. DockerBackend executes commands inside containers for sandboxing.

### D

**DockerBackend**
Backend that provides sandboxed execution in Docker containers. Supports full isolation with volume mounts for data access.

### E

**execute Tool**
SDK tool generated by FilesystemMiddleware that executes commands in the configured backend (Docker, Remote, etc.).

**Execution Environment**
Where agent operations actually run. Can be host system (CLI), Docker container, remote server, or custom environment.

### F

**FilesystemBackend**
Backend that provides file operations (read/write/ls/glob/grep) on a specific directory. Does not support command execution.

**FilesystemMiddleware**
Middleware that generates file operation tools and the execute tool from backend capabilities. Routes tool calls to appropriate backend.

**Frontend (Virtual vs Physical)**
- **Virtual Path**: Path seen by agent (e.g., `/workspace/`)
- **Physical Path**: Actual path on host system (e.g., `/host/workspace/`)
- FilesystemBackend with `virtual_mode=True` maps between them

### G

**Glob**
Pattern matching tool for finding files by name pattern (e.g., `**/*.py` finds all Python files).

**Grep**
Content search tool for finding text patterns within files.

### H

**Hooks**
Functions in middleware that execute at specific points in the agent lifecycle:
- `before_model()` - Before model invocation
- `after_model()` - After model invocation
- `modify_tools()` - Modify available tools

### L

**LangChain**
Framework for building applications with large language models. DeepAgents builds on LangChain v1.0.

**LangGraph**
LangChain's graph-based orchestration system for building stateful agents.

### M

**Middleware**
Composable functionality layers that intercept and modify agent behavior. Examples: FilesystemMiddleware, SkillsMiddleware, SubAgentMiddleware.

**Middleware Stack**
Ordered list of middleware that execute in sequence. Order matters!

### P

**Progressive Disclosure**
Skills pattern where information is loaded incrementally:
1. Level 1: Name + description (~100 tokens)
2. Level 2: Full SKILL.md (~5000 tokens)
3. Level 3: Scripts and resources (as needed)

### R

**RemoteBackend**
Backend that executes operations on remote servers via SSH. Used for distributed computing and cloud execution.

**Routes**
In CompositeBackend, path prefix mappings that direct operations to specific backends. Example: `/skills/` → FilesystemBackend.

**Runtime**
Execution context for agents, providing access to state management and backend operations. Required for StateBackend creation.

### S

**SandboxBackendProtocol**
Backend protocol that includes execution capability (`execute()` method). DockerBackend and RemoteBackend implement this.

**SDK Approach**
Building AI agents using the DeepAgents SDK with pluggable backends, middleware stacks, and programmatic control.

**SKILL.md**
Structured documentation file that defines a skill. Contains YAML frontmatter (name, description) and usage instructions.

**SkillsMiddleware**
Middleware that discovers skills from specified directories and injects skill documentation into agent context using progressive disclosure.

**StateBackend**
Special backend that manages agent conversation state (messages, checkpoints, metadata). Required for every agent.

**SubAgentMiddleware**
Middleware that enables task delegation by providing a `task()` tool that creates and manages sub-agents.

**SummarizationMiddleware**
Middleware that automatically summarizes conversation history when token limits are approached.

**System Prompt**
Initial instructions provided to the agent defining its role, capabilities, and behavior.

### T

**TodoListMiddleware**
Middleware that provides task tracking tools: `add_todo()`, `complete_todo()`, `list_todos()`, `update_todo()`.

**Tool**
Function that an agent can call to perform actions. Tools are generated by middleware or defined manually.

**Tool Call**
When an agent decides to use a tool, it makes a "tool call" with specific parameters. The tool executes and returns a result.

### V

**Virtual Mode**
FilesystemBackend configuration where paths are presented to the agent differently than their physical location on the host.

**Volume Mount**
Docker feature that makes a host directory accessible inside a container. Required for DockerBackend to access workspace and skills.

### W

**Workdir**
Working directory for command execution. Set in backend configuration (DockerBackend, RemoteBackend) or per-command.

**Workspace**
Directory where agent performs file operations and stores generated files. Typically `/workspace/` in virtual paths.

---

## 17. Additional Resources

### 17.1 Official Documentation

- **DeepAgents SDK**: [github.com/deepagents/deepagents](https://github.com/deepagents/deepagents)
- **Agent Skills Standard**: [agentskills.io](https://agentskills.io/)
- **LangChain v1.0**: [python.langchain.com](https://python.langchain.com/)
- **Claude API**: [docs.anthropic.com](https://docs.anthropic.com/)

### 17.2 Related Documentation in This Repository

- `ai_docs/langchain_middleware.md` - LangChain middleware design principles
- `ai_docs/agent-skills.md` - Agent Skills specification
- `ai_docs/langchain-v1.0.md` - LangChain v1.0 technical reference
- `examples/skill-agent/` - Full SDK implementation example
- `examples/skill-agent/README.md` - Skill agent setup guide
- `examples/skill-agent/backends/DOCKER_SETUP.md` - Docker backend setup

### 17.3 Code Examples

**Minimal Examples**:
- `examples/skill-agent/agent.py` - Production-ready agent implementation
- `examples/skill-agent/backends/docker_backend.py` - Custom Docker backend
- `examples/skill-agent/middleware/` - Custom middleware implementations

**Skills Examples**:
- `examples/skill-agent/skills/file-hash/` - Cryptographic hash calculation skill
- `examples/skill-agent/skills/*/SKILL.md` - Various skill documentation examples

### 17.4 Community Resources

- **GitHub Issues**: Report bugs, request features, ask questions
- **Discord/Slack**: Community discussions (if available)
- **Stack Overflow**: Tag questions with `deepagents`, `langchain`

### 17.5 Docker Resources

- **Docker Documentation**: [docs.docker.com](https://docs.docker.com/)
- **Docker Python SDK**: [docker-py.readthedocs.io](https://docker-py.readthedocs.io/)
- **Dockerfile Best Practices**: [docs.docker.com/develop/dev-best-practices](https://docs.docker.com/develop/dev-best-practices/)

### 17.6 Further Reading

**AI Agents**:
- "Building Effective Agents" - Anthropic Engineering Blog
- "LangChain Conceptual Guide" - LangChain Documentation
- "Agent Skills: Equipping Agents for the Real World" - Anthropic Blog

**Software Architecture**:
- "Middleware Design Patterns" - Web development patterns applicable to AI agents
- "Backend Abstractions" - Designing pluggable systems
- "Progressive Enhancement" - Loading information incrementally

---

## Conclusion

This document has covered the complete architecture comparison between CLI and SDK approaches for building AI agents with DeepAgents.

### Key Takeaways

1. **CLI is simple** - Great for learning, prototyping, personal use
2. **SDK is powerful** - Production-ready, sandboxed, highly customizable
3. **Choose based on needs** - Security, scalability, complexity requirements
4. **Hybrid is possible** - Develop with CLI, deploy with SDK
5. **Start simple, scale up** - Begin with minimal setup, add features as needed

### Next Steps

**For Beginners**:
1. Try Claude Code CLI to understand agent behavior
2. Read Section 10 (Implementation Patterns)
3. Build a minimal SDK agent (Pattern 1)
4. Gradually add features

**For Production**:
1. Review Section 11 (Comparison Tables)
2. Use Decision Framework (Section 9)
3. Implement full-featured pattern (Pattern 5)
4. Set up monitoring and logging

**For Custom Needs**:
1. Study Backend Protocol (Section 5.6)
2. Implement custom backend
3. Create custom middleware
4. Integrate with existing infrastructure

### Contributing

Found an error? Have a suggestion? Please contribute:
- Open issues in the repository
- Submit pull requests with improvements
- Share your implementation patterns
- Help improve documentation

---

**Document Version**: 1.0
**Last Updated**: 2026-01-21
**Maintained By**: AI Agent Template Project

For questions or feedback, please see the project repository.


---

**Navigation**: [⬅️ Part 7: Migration & Troubleshooting](part7-migration-troubleshooting.md) | [Index](INDEX.md)

---

**🎉 You've reached the end of the DeepAgents CLI vs SDK Architecture documentation!**

Return to [Index](INDEX.md) for navigation or explore related documentation in the repository.
