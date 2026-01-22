# DeepAgents CLI vs SDK Architecture - Part 1: Overview

> **Navigation**: [⬅️ Index](INDEX.md) | [Part 2: Core Concepts ➡️](part2-core-concepts.md)

**Sections**: 1-3 | Executive Summary, CLI vs SDK Overview, Architecture Comparison

---

# DeepAgents CLI vs SDK Architecture

> Comprehensive technical documentation comparing DeepAgents CLI and SDK approaches, including module architecture flows, backend systems, and implementation patterns.

**Version:** 1.0
**Last Updated:** 2026-01-21
**Target Audience:** Engineers implementing DeepAgents-based AI agents

---

## Sources and References

### Official Documentation
- [DeepAgents GitHub Repository](https://github.com/deepagents/deepagents)
- [Agent Skills Open Standard](https://agentskills.io/)
- [LangChain v1.0 Documentation](https://python.langchain.com/)

### Related Documentation in This Repository
- `ai_docs/langchain_middleware.md` - LangChain middleware design principles
- `ai_docs/agent-skills.md` - Agent Skills specification
- `ai_docs/langchain-v1.0.md` - LangChain v1.0 technical reference
- `examples/skill-agent/` - Full SDK implementation example

### Key Source Files
- `examples/skill-agent/agent.py` - Main SDK implementation
- `examples/skill-agent/backends/docker_backend.py` - Custom Docker backend
- `deepagents/middleware/filesystem.py` - Filesystem middleware implementation
- `deepagents/middleware/skills.py` - Skills discovery and injection
- `deepagents/backends/protocol.py` - Backend protocol definitions

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Overview: CLI vs SDK](#2-overview-cli-vs-sdk)
3. [Architecture Comparison](#3-architecture-comparison)
4. [Core Concepts](#4-core-concepts)
5. [Backend Implementations Deep Dive](#5-backend-implementations-deep-dive)
6. [Middleware Comparison](#6-middleware-comparison)
7. [Execution Mechanisms](#7-execution-mechanisms)
8. [Skills System](#8-skills-system)
9. [Decision Framework](#9-decision-framework)
10. [Implementation Patterns](#10-implementation-patterns)
11. [Comparison Tables](#11-comparison-tables)
12. [Common Patterns and Anti-Patterns](#12-common-patterns-and-anti-patterns)
13. [Migration Guide](#13-migration-guide)
14. [Troubleshooting](#14-troubleshooting)
15. [FAQ](#15-faq)
16. [Glossary](#16-glossary)

---

## 1. Executive Summary

### What This Document Covers

This document provides a comprehensive comparison of two approaches to building AI agents with DeepAgents:

1. **CLI Approach** - Using Claude Code CLI or similar tools where the agent sends bash commands to the host system
2. **SDK Approach** - Using the DeepAgents SDK to build custom agents with sandboxed execution environments

### Quick Decision Tree

```
Do you need sandboxed execution?
├─ YES → Use SDK with DockerBackend or RemoteBackend
│         - Production deployments
│         - Multi-user environments
│         - Security-critical applications
│
└─ NO → Consider CLI approach or SDK with ShellMiddleware
         ├─ Need custom middleware/backends? → Use SDK
         ├─ Need rapid prototyping? → Use CLI
         └─ Need portability? → Use SDK with StateBackend only
```

### Key Differences at a Glance

| Aspect | CLI Approach | SDK Approach |
|--------|-------------|--------------|
| **Execution Model** | Agent → bash → Host system | Agent → Backend → Sandboxed environment |
| **Sandboxing** | None (runs on host) | Full (Docker/Remote) |
| **Complexity** | Low | Medium to High |
| **Flexibility** | Limited | High |
| **Security** | Trusts agent fully | Sandboxed execution |
| **Use Case** | Development, trusted environments | Production, multi-user, security-critical |

### When to Read Which Sections

- **Quick start?** → Section 9 (Decision Framework) and Section 10 (Implementation Patterns)
- **Understanding architecture?** → Sections 2-4 (Overview, Architecture, Core Concepts)
- **Building custom backends?** → Section 5 (Backend Implementations)
- **Working with skills?** → Section 8 (Skills System)
- **Migrating between approaches?** → Section 13 (Migration Guide)
- **Troubleshooting issues?** → Section 14 (Troubleshooting)

---

## 2. Overview: CLI vs SDK

### 2.1 What is the CLI Approach?

The **CLI approach** refers to using AI agents that interact with the host system through bash commands. Examples include:

- **Claude Code CLI** - Anthropic's official CLI tool
- **Custom CLI tools** - Built with similar architecture

#### Execution Model

```
User Request
    ↓
AI Agent (Claude)
    ↓
Bash Tool Call
    ↓
Host System (direct execution)
    ↓
Result back to Agent
```

#### Key Characteristics

1. **Direct Host Access**: Commands run directly on the host system with full privileges
2. **Minimal Abstraction**: Agent interacts with system through standard bash/shell
3. **No Sandboxing**: All operations execute with user's permissions
4. **Stateless Tools**: Each bash command is independent
5. **Simple Architecture**: Few layers between agent and system

#### Example CLI Interaction

```python
# Agent receives user request: "Create a Python script to calculate Fibonacci"

# Agent makes tool call:
bash(
    command="cat > fib.py << 'EOF'\ndef fibonacci(n):\n    if n <= 1:\n        return n\n    return fibonacci(n-1) + fibonacci(n-2)\n\nprint(fibonacci(10))\nEOF",
    description="Create Fibonacci script"
)

# Command executes directly on host
# File fib.py created in current directory

# Agent makes another tool call:
bash(
    command="python fib.py",
    description="Run Fibonacci script"
)

# Output: 55
```

### 2.2 What is the SDK Approach?

The **SDK approach** uses the DeepAgents framework to build custom agents with:

- **Backend abstraction** - Pluggable execution environments
- **Middleware stack** - Composable functionality layers
- **Sandboxed execution** - Isolated environments (Docker, remote, etc.)
- **Tool management** - Programmatic tool definition and discovery

#### Execution Model

```
User Request
    ↓
AI Agent (LangChain + DeepAgents)
    ↓
Middleware Stack (FilesystemMiddleware, SkillsMiddleware, etc.)
    ↓
Backend Layer (DockerBackend, RemoteBackend, etc.)
    ↓
Sandboxed Environment (Docker container, remote server, etc.)
    ↓
Result → Backend → Middleware → Agent
```

#### Key Characteristics

1. **Backend Abstraction**: Execution environment is pluggable and configurable
2. **Middleware Composition**: Functionality added through middleware layers
3. **Sandboxing Support**: Built-in support for isolated execution
4. **Tool Discovery**: Automatic tool generation from backend capabilities
5. **State Management**: Explicit state handling through StateBackend
6. **Flexible Architecture**: Many layers, high customization

#### Example SDK Interaction

```python
# Create agent with DockerBackend
from deepagents.backends import DockerBackend
from deepagents.middleware.filesystem import FilesystemMiddleware

backend = DockerBackend(
    image="python:3.11",
    container_name="agent-sandbox",
    workdir="/workspace",
    volumes={"/host/workspace": "/workspace"}
)

agent = create_agent(
    model=model,
    middleware=[FilesystemMiddleware(backend=lambda rt: backend)],
    tools=[]
)

# Agent receives user request: "Create a Python script to calculate Fibonacci"

# Agent makes tool call:
write_file(
    path="/workspace/fib.py",
    content="""def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)

print(fibonacci(10))"""
)

# Backend routes to DockerBackend
# File created inside Docker container at /workspace/fib.py

# Agent makes another tool call:
execute(command="python /workspace/fib.py")

# Backend executes inside Docker container
# Output: 55
```

### 2.3 Philosophical Differences

#### Trust Model

**CLI Approach**:
- Assumes full trust in the AI agent
- Agent has complete access to host system
- No protection against malicious or erroneous commands
- Suitable for single-user, development environments

**SDK Approach**:
- Supports zero-trust architecture
- Agent operates in sandboxed environment
- Protection against harmful operations
- Suitable for production, multi-user environments

#### Flexibility vs Simplicity

**CLI Approach**:
- **Simplicity**: Minimal setup, direct execution
- **Limited flexibility**: Hard to customize execution environment
- **Fast iteration**: No build/deployment steps

**SDK Approach**:
- **High flexibility**: Custom backends, middleware, tools
- **Higher complexity**: More setup, configuration required
- **Structured development**: Clear separation of concerns

#### Tool Management

**CLI Approach**:
- Tools are CLI primitives (bash, read, write, etc.)
- Tools defined by CLI implementation
- Limited customization

**SDK Approach**:
- Tools generated dynamically from backend capabilities
- Custom tools through middleware
- Full programmatic control

#### State Management

**CLI Approach**:
- Implicit state (filesystem, environment variables)
- No explicit state backend
- State is "whatever the host system has"

**SDK Approach**:
- Explicit StateBackend for agent state
- Separate execution state from agent state
- Portable state across different execution environments

### 2.4 When Each Approach Makes Sense

#### Use CLI Approach When:

1. **Rapid Prototyping**: Quick experimentation, no production requirements
2. **Development Environment**: Single developer, trusted commands
3. **Personal Automation**: User's own machine, user-level tasks
4. **Learning/Exploration**: Understanding AI agent behavior
5. **Simple Tasks**: File operations, basic scripting, no complex requirements

#### Use SDK Approach When:

1. **Production Deployment**: Serving multiple users, reliability requirements
2. **Security Requirements**: Need sandboxing, isolation, access control
3. **Custom Functionality**: Need custom backends, middleware, or tools
4. **Complex Workflows**: Multi-step processes, skill management
5. **Scalability**: Distributed execution, remote backends
6. **Portability**: Run same agent in different environments

#### Hybrid Approach

You can combine both:
- **CLI for development** - Rapid iteration using Claude Code
- **SDK for deployment** - Production version with sandboxing
- **SDK with ShellMiddleware** - SDK architecture with direct shell access

---

## 3. Architecture Comparison

### 3.1 CLI Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                         User                                 │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ↓
┌─────────────────────────────────────────────────────────────┐
│                    CLI Application                           │
│  (e.g., Claude Code CLI)                                    │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              AI Agent (Claude)                        │  │
│  │  - Receives user requests                            │  │
│  │  - Makes tool calls                                  │  │
│  │  - Processes results                                 │  │
│  └────────────────┬─────────────────────────────────────┘  │
│                   │                                          │
│                   ↓                                          │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              Tool Layer                               │  │
│  │  - bash(command, description, timeout)               │  │
│  │  - read(file_path)                                   │  │
│  │  - write(file_path, content)                         │  │
│  │  - edit(file_path, old_string, new_string)          │  │
│  └────────────────┬─────────────────────────────────────┘  │
└───────────────────┼──────────────────────────────────────────┘
                    │
                    ↓
┌─────────────────────────────────────────────────────────────┐
│                    Host System                               │
│  - Direct command execution                                 │
│  - Full filesystem access                                   │
│  - No isolation or sandboxing                               │
└─────────────────────────────────────────────────────────────┘
```

#### CLI Execution Flow

1. **User Request** → CLI receives user input
2. **Agent Processing** → Claude analyzes request, decides on actions
3. **Tool Selection** → Agent chooses bash/read/write/edit tools
4. **Direct Execution** → Commands run on host with user privileges
5. **Result Collection** → Output returned to agent
6. **Response Generation** → Agent synthesizes results into user response

### 3.2 SDK Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                         User                                 │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ↓
┌─────────────────────────────────────────────────────────────┐
│                  Custom Application                          │
│  (Built with DeepAgents SDK)                                │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │         AI Agent (LangChain + DeepAgents)            │  │
│  │  - create_agent() or create_deep_agent()            │  │
│  │  - Manages conversation state                        │  │
│  │  - Invokes middleware chain                          │  │
│  └────────────────┬─────────────────────────────────────┘  │
│                   │                                          │
│                   ↓                                          │
│  ┌──────────────────────────────────────────────────────┐  │
│  │            Middleware Stack                           │  │
│  │  (Composable layers, executed in order)             │  │
│  │                                                       │  │
│  │  [TodoListMiddleware]                                │  │
│  │         ↓                                            │  │
│  │  [SkillsMiddleware] ← Skills discovery              │  │
│  │         ↓                                            │  │
│  │  [FilesystemMiddleware] ← Tool generation           │  │
│  │         ↓                                            │  │
│  │  [SubAgentMiddleware] ← Task delegation             │  │
│  │         ↓                                            │  │
│  │  [CustomMiddleware] ← Your custom logic             │  │
│  └────────────────┬─────────────────────────────────────┘  │
│                   │                                          │
│                   ↓                                          │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              Backend Layer                            │  │
│  │  (Pluggable execution environment)                   │  │
│  │                                                       │  │
│  │  StateBackend ← Agent state management              │  │
│  │         +                                            │  │
│  │  FilesystemBackend / DockerBackend / RemoteBackend  │  │
│  │         +                                            │  │
│  │  CompositeBackend ← Path routing                    │  │
│  └────────────────┬─────────────────────────────────────┘  │
└───────────────────┼──────────────────────────────────────────┘
                    │
                    ↓
┌─────────────────────────────────────────────────────────────┐
│              Execution Environment                           │
│  (Sandboxed or Remote)                                      │
│                                                              │
│  [Docker Container]  OR  [Remote Server]  OR  [Host]       │
│  - Isolated filesystem                                      │
│  - Controlled access                                        │
│  - Volume mounts for data sharing                           │
└─────────────────────────────────────────────────────────────┘
```

#### SDK Execution Flow

1. **User Request** → Application receives input
2. **Agent Processing** → LangChain agent with custom middleware
3. **Middleware Chain** → Each middleware processes request in sequence
   - **TodoListMiddleware**: Manages task tracking
   - **SkillsMiddleware**: Discovers and injects skill documentation
   - **FilesystemMiddleware**: Generates file and execute tools
   - **SubAgentMiddleware**: Enables task delegation
4. **Backend Routing** → CompositeBackend routes operations to appropriate backend
5. **Execution** → Backend executes in sandboxed environment
6. **Result Propagation** → Results flow back through middleware chain
7. **Response Generation** → Agent synthesizes response

### 3.3 Component Comparison

#### Tool Layer

**CLI**:
```
bash(command, description, timeout)
read(file_path, offset, limit)
write(file_path, content)
edit(file_path, old_string, new_string)
glob(pattern, path)
grep(pattern, path, options)
```

**SDK**:
```python
# Tools generated dynamically by FilesystemMiddleware
# based on backend capabilities

ls(path)
read_file(path)
write_file(path, content)
edit_file(path, old_content, new_content)
glob(pattern)
grep(pattern, path)
execute(command, workdir)  # If backend supports execution

# Plus custom tools from other middleware
task(instructions, agent_type)  # From SubAgentMiddleware
```

#### State Management

**CLI**:
- No explicit StateBackend
- State is implicit (filesystem, environment)
- Conversation state managed by CLI application

**SDK**:
```python
# Explicit StateBackend factory
backend = lambda rt: CompositeBackend(
    default=DockerBackend(...),
    state_backend=StateBackend(runtime=rt),  # Agent state
    routes={
        "/workspace/": FilesystemBackend(...),  # File operations
    }
)
```

#### Middleware Layer

**CLI**:
- No middleware abstraction
- All functionality baked into CLI
- Limited customization

**SDK**:
```python
middleware_stack = [
    TodoListMiddleware(),
    SkillsMiddleware(backend=backend, sources=["/skills/"]),
    FilesystemMiddleware(backend=backend),
    SubAgentMiddleware(default_model=model, ...),
    CustomMiddleware(),  # Your custom logic
]
```

### 3.4 Data Flow Comparison

#### CLI Data Flow: File Read Operation

```
User: "Read the contents of config.json"
     ↓
Agent decides: Use read() tool
     ↓
read(file_path="/path/to/config.json")
     ↓
CLI executes: cat /path/to/config.json
     ↓
Host filesystem (direct read)
     ↓
Result: {"key": "value"}
     ↓
Agent receives result
     ↓
Agent: "The config contains..."
```

#### SDK Data Flow: File Read Operation

```
User: "Read the contents of config.json"
     ↓
Agent decides: Use read_file() tool (from FilesystemMiddleware)
     ↓
Middleware chain: before_model hooks
     ↓
Tool call: read_file(path="/workspace/config.json")
     ↓
FilesystemMiddleware intercepts tool call
     ↓
Backend routing: CompositeBackend resolves path
     ↓
Path /workspace/* → routes to FilesystemBackend (fast host read)
     ↓
FilesystemBackend.read_file("/workspace/config.json")
     ↓
Host filesystem (mapped from /host/workspace/config.json)
     ↓
Result: {"key": "value"}
     ↓
Backend → Middleware → Agent
     ↓
Agent: "The config contains..."
```

#### SDK Data Flow: Execute Operation (Docker)

```
User: "Run the Python script analysis.py"
     ↓
Agent decides: Use execute() tool
     ↓
Middleware chain processes
     ↓
Tool call: execute(command="python /workspace/analysis.py")
     ↓
FilesystemMiddleware intercepts
     ↓
Backend routing: CompositeBackend resolves
     ↓
No route match for execute → falls to default backend (DockerBackend)
     ↓
DockerBackend.execute("python /workspace/analysis.py")
     ↓
Docker container: docker exec skill-agent-container python /workspace/analysis.py
     ↓
Container has /workspace mounted from host
     ↓
Python runs inside container (sandboxed)
     ↓
Result: "Analysis complete: ..."
     ↓
Docker → Backend → Middleware → Agent
     ↓
Agent: "The analysis shows..."
```

---


---

**Navigation**: [⬅️ Index](INDEX.md) | [Part 2: Core Concepts ➡️](part2-core-concepts.md)
