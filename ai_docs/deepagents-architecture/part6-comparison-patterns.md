# DeepAgents CLI vs SDK Architecture - Part 6: Comparison & Patterns

> **Navigation**: [⬅️ Part 5: Implementation](part5-implementation.md) | [Index](INDEX.md) | [Part 7: Migration & Troubleshooting ➡️](part7-migration-troubleshooting.md)

**Sections**: 11-12 | Comparison Tables, Common Patterns and Anti-Patterns

---

## 11. Comparison Tables

Comprehensive comparison tables for quick reference.

### 11.1 Feature Matrix

| Feature | CLI | SDK Minimal | SDK Docker | SDK Full |
|---------|-----|------------|-----------|----------|
| **Execution** |
| Direct host execution | ✓ | ✗ | ✗ | ✗ |
| Sandboxed execution | ✗ | ✗ | ✓ | ✓ |
| Remote execution | ✗ | ✗ | ✗ | ✓ |
| **File Operations** |
| Read files | ✓ | ✓ | ✓ | ✓ |
| Write files | ✓ | ✓ | ✓ | ✓ |
| Edit files | ✓ | ✓ | ✓ | ✓ |
| **Advanced Features** |
| Skills system | ✗ | ✗ | ✓ | ✓ |
| Task delegation | ✗ | ✗ | ✗ | ✓ |
| Custom middleware | ✗ | ✓ | ✓ | ✓ |
| Custom backends | ✗ | ✓ | ✓ | ✓ |
| **Characteristics** |
| Setup complexity | Low | Low | Medium | High |
| Flexibility | Low | Medium | High | Very High |
| Security | Low | Medium | High | Very High |
| Performance | High | High | Medium | Medium |
| Suitable for production | ✗ | ✗ | ✓ | ✓ |

### 11.2 Performance Characteristics

| Operation | CLI | SDK FilesystemBackend | SDK DockerBackend | SDK RemoteBackend |
|-----------|-----|----------------------|-------------------|-------------------|
| File read (small) | ~0.1ms | ~0.1ms | ~10ms | ~50-200ms |
| File write (small) | ~1ms | ~1ms | ~15ms | ~50-200ms |
| Command execution | ~10-50ms | N/A | ~20-100ms | ~100-500ms |
| Skills discovery | N/A | ~100ms | ~100ms | ~200ms |
| Container startup | N/A | N/A | ~1-2s | N/A |
| Memory overhead | ~50MB | ~50MB | ~150MB | ~50MB |

**Notes**:
- Times are approximate and vary by system
- DockerBackend overhead is per-command execution
- Container startup is one-time cost (with auto_start)
- RemoteBackend times depend on network latency

### 11.3 Security Comparison

| Security Aspect | CLI | SDK FilesystemBackend | SDK DockerBackend | SDK RemoteBackend |
|----------------|-----|----------------------|-------------------|-------------------|
| Process isolation | ✗ | ✗ | ✓ | ✓ |
| Filesystem isolation | ✗ | Partial* | ✓ | ✓ |
| Network isolation | ✗ | ✗ | ✓ (optional) | ✓ |
| Resource limits | ✗ | ✗ | ✓ | ✓ |
| User permissions | Host user | Host user | Container user | Remote user |
| Suitable for untrusted code | ✗ | ✗ | ✓ | ✓ |
| Multi-tenant safe | ✗ | ✗ | ✓ | ✓ |

*FilesystemBackend can restrict access to a specific directory but doesn't prevent escape via symlinks or other filesystem features.

### 11.4 Backend Capabilities Matrix

| Capability | StateBackend | FilesystemBackend | DockerBackend | RemoteBackend | CompositeBackend |
|-----------|--------------|-------------------|---------------|---------------|------------------|
| Agent state management | ✓ | ✗ | ✗ | ✗ | ✓ (delegates) |
| read_file | ✗ | ✓ | ✓ | ✓ | ✓ (routes) |
| write_file | ✗ | ✓ | ✓ | ✓ | ✓ (routes) |
| ls | ✗ | ✓ | ✓ | ✓ | ✓ (routes) |
| glob | ✗ | ✓ | ✓ | ✓ | ✓ (routes) |
| grep | ✗ | ✓ | ✓ | ✓ | ✓ (routes) |
| execute | ✗ | ✗ | ✓ | ✓ | ✓ (routes) |
| Path routing | ✗ | ✗ | ✗ | ✗ | ✓ |
| Sandboxing | N/A | ✗ | ✓ | ✓ | ✓ (if default supports) |

### 11.5 Middleware Responsibilities

| Middleware | Tool Generation | State Modification | Backend Interaction | Event Handling |
|-----------|----------------|-------------------|--------------------|--------------  |
| FilesystemMiddleware | ✓ (file + execute) | ✗ | ✓ (routes calls) | ✗ |
| SkillsMiddleware | ✗ | ✓ (system prompt) | ✓ (reads SKILL.md) | ✗ |
| SubAgentMiddleware | ✓ (task tool) | ✗ | ✗ | ✓ (optional streaming) |
| TodoListMiddleware | ✓ (todo tools) | ✓ (todo state) | ✗ | ✗ |
| SummarizationMiddleware | ✗ | ✓ (summarizes messages) | ✗ | ✗ |

### 11.6 Use Case Recommendations

| Use Case | Best Approach | Required Components |
|----------|--------------|-------------------|
| Personal automation | CLI | Claude Code CLI |
| Learning/Education | CLI | Claude Code CLI |
| Development/Testing | CLI or SDK Minimal | Model + StateBackend |
| Code execution agent | SDK Docker | DockerBackend + FilesystemMiddleware |
| Data science agent | SDK Full | Docker + Skills + SubAgents |
| Multi-user service | SDK Docker | DockerBackend with resource limits |
| Distributed system | SDK Remote | RemoteBackend + CompositeBackend |
| Security-critical | SDK Docker | DockerBackend + custom monitoring |
| Cloud deployment | SDK Custom | Custom Backend for cloud services |
| Edge devices | SDK Minimal | Lightweight backend, no Docker |

---

## 12. Common Patterns and Anti-Patterns

This section covers best practices (patterns) and common mistakes (anti-patterns).

### 12.1 Patterns (Best Practices)

#### Pattern: Backend Factory with Runtime

**✓ Correct**:
```python
# Use lambda factory to defer backend creation
backend_factory = lambda rt: CompositeBackend(
    default=DockerBackend(...),
    state_backend=StateBackend(runtime=rt),  # Runtime injected at execution time
    routes={...}
)

middleware = [
    FilesystemMiddleware(backend=backend_factory)
]
```

**Rationale**: StateBackend requires runtime reference, which is only available during agent execution.

#### Pattern: CompositeBackend for Performance

**✓ Correct**:
```python
# Fast host reads, sandboxed execution
backend = CompositeBackend(
    default=DockerBackend(...),  # Execution
    routes={
        "/skills/": FilesystemBackend(...),  # Fast reads
        "/workspace/": FilesystemBackend(...),  # Fast reads
    }
)
```

**Rationale**: File reads from host are 10-100x faster than from Docker container.

#### Pattern: Volume Mounts Match Routes

**✓ Correct**:
```python
# Docker backend with volumes matching CompositeBackend routes
docker = DockerBackend(
    volumes={
        "/host/skills": "/skills",      # Matches route /skills/
        "/host/workspace": "/workspace", # Matches route /workspace/
    }
)

composite = CompositeBackend(
    default=docker,
    routes={
        "/skills/": FilesystemBackend(root_dir="/host/skills", ...),
        "/workspace/": FilesystemBackend(root_dir="/host/workspace", ...),
    }
)
```

**Rationale**: Routes handle reads, Docker handles execution - volumes ensure container can access files.

#### Pattern: Skills Before Filesystem Middleware

**✓ Correct**:
```python
middleware = [
    SkillsMiddleware(...),      # Discovers skills first
    FilesystemMiddleware(...),  # Provides file tools
]
```

**Rationale**: Skills should be discovered before file operations become available.

#### Pattern: Explicit StateBackend in CompositeBackend

**✓ Correct**:
```python
backend_factory = lambda rt: CompositeBackend(
    default=DockerBackend(...),
    state_backend=StateBackend(runtime=rt),  # Explicit
    routes={...}
)
```

**Rationale**: Makes state management explicit and avoids confusion.

### 12.2 Anti-Patterns (Common Mistakes)

#### Anti-Pattern: Creating Backend Without Factory

**✗ Wrong**:
```python
# This will fail - StateBackend needs runtime
backend = CompositeBackend(
    default=DockerBackend(...),
    state_backend=StateBackend(runtime=???),  # No runtime available yet!
    routes={...}
)

middleware = [
    FilesystemMiddleware(backend=backend)  # Won't work
]
```

**✓ Correct**:
```python
# Use factory pattern
backend_factory = lambda rt: CompositeBackend(
    default=DockerBackend(...),
    state_backend=StateBackend(runtime=rt),
    routes={...}
)

middleware = [
    FilesystemMiddleware(backend=backend_factory)  # Factory, not instance
]
```

#### Anti-Pattern: Forgetting Volume Mounts

**✗ Wrong**:
```python
# Docker backend without volumes
docker = DockerBackend(
    image="python:3.11",
    workdir="/workspace",
    # No volumes!
)

composite = CompositeBackend(
    default=docker,
    routes={
        "/skills/": FilesystemBackend(root_dir="/host/skills", ...),
    }
)

# Agent calls: execute("python /skills/script.py")
# Container doesn't have /skills/ mounted - fails!
```

**✓ Correct**:
```python
docker = DockerBackend(
    image="python:3.11",
    workdir="/workspace",
    volumes={
        "/host/skills": "/skills",  # Mount skills directory
    }
)
```

#### Anti-Pattern: Wrong Middleware Order

**✗ Wrong**:
```python
middleware = [
    SubAgentMiddleware(...),     # Sub-agents won't have skills!
    SkillsMiddleware(...),       # Skills discovered too late
]
```

**✓ Correct**:
```python
middleware = [
    SkillsMiddleware(...),       # Discover skills first
    SubAgentMiddleware(...),     # Sub-agents inherit skills
]
```

#### Anti-Pattern: No Virtual Mode in Routes

**✗ Wrong**:
```python
# FilesystemBackend without virtual_mode
routes={
    "/workspace/": FilesystemBackend(
        root_dir="/host/workspace",
        virtual_mode=False  # Agent must use /host/workspace/ paths
    ),
}

# Agent must know about /host/workspace/ (leaks implementation)
```

**✓ Correct**:
```python
routes={
    "/workspace/": FilesystemBackend(
        root_dir="/host/workspace",
        virtual_mode=True  # Agent uses /workspace/ paths
    ),
}

# Agent uses clean /workspace/ paths
```

#### Anti-Pattern: Using FilesystemBackend for Execution

**✗ Wrong**:
```python
backend = FilesystemBackend(root_dir="/workspace")

# Agent calls: execute("python script.py")
# FilesystemBackend doesn't support execute() - fails!
```

**✓ Correct**:
```python
# Use backend with execution capability
backend = DockerBackend(...)

# Or use CompositeBackend
backend = CompositeBackend(
    default=DockerBackend(...),  # Has execute()
    routes={
        "/workspace/": FilesystemBackend(...),  # Only file ops
    }
)
```

#### Anti-Pattern: Hardcoding Paths

**✗ Wrong**:
```python
# Hardcoded paths
backend = FilesystemBackend(root_dir="/home/user/project/workspace")

# Not portable, breaks on other machines
```

**✓ Correct**:
```python
from pathlib import Path

# Use relative or configurable paths
workspace_path = Path("./workspace").resolve()
backend = FilesystemBackend(root_dir=str(workspace_path))

# Or use environment variables
import os
workspace_path = os.environ.get("WORKSPACE_PATH", "./workspace")
```

#### Anti-Pattern: Forgetting auto_start

**✗ Wrong**:
```python
docker = DockerBackend(
    image="python:3.11",
    container_name="agent-sandbox",
    # auto_start=False (default)
)

# First execute() call will fail if container doesn't exist
```

**✓ Correct**:
```python
docker = DockerBackend(
    image="python:3.11",
    container_name="agent-sandbox",
    auto_start=True,  # Creates/starts container automatically
)
```

#### Anti-Pattern: Skills Without Execution

**✗ Wrong**:
```python
# Agent has skills but no way to execute them
middleware = [
    SkillsMiddleware(backend=backend_factory, sources=["/skills/"]),
    # No FilesystemMiddleware - no execute() tool!
]

# Agent sees skills but can't run them
```

**✓ Correct**:
```python
middleware = [
    SkillsMiddleware(backend=backend_factory, sources=["/skills/"]),
    FilesystemMiddleware(backend=backend_factory),  # Provides execute()
]
```

### 12.3 Performance Patterns

#### Pattern: Route High-Frequency Reads to FilesystemBackend

**✓ Correct**:
```python
# Skills are read frequently during discovery
composite = CompositeBackend(
    default=DockerBackend(...),
    routes={
        "/skills/": FilesystemBackend(...),  # Fast host reads
    }
)

# Skills discovery: fast
# Skills execution: sandboxed
```

#### Pattern: Reuse Docker Containers

**✓ Correct**:
```python
docker = DockerBackend(
    container_name="agent-sandbox",
    auto_start=True,
    auto_remove=False,  # Don't remove container after use
)

# Container persists across agent invocations
# Saves 1-2s startup time per request
```

#### Anti-Pattern: Creating New Containers Per Request

**✗ Wrong**:
```python
# Creating new backend per request
def handle_request(user_input):
    backend = DockerBackend(...)  # New container each time!
    agent = create_agent(...)
    return agent.invoke(...)

# Each request pays container startup cost (~1-2s)
```

**✓ Correct**:
```python
# Create backend once, reuse
backend = DockerBackend(auto_start=True, auto_remove=False)

def handle_request(user_input):
    # Reuse existing backend/container
    agent = create_agent(middleware=[FilesystemMiddleware(backend=...)])
    return agent.invoke(...)
```

### 12.4 Security Patterns

#### Pattern: Resource Limits

**✓ Correct**:
```python
docker = DockerBackend(
    mem_limit="1g",      # Limit memory
    cpu_quota=50000,     # Limit CPU (50% of one core)
)

# Prevents resource exhaustion attacks
```

#### Pattern: Read-Only Mounts for Sensitive Data

**✓ Correct**:
```python
docker = DockerBackend(
    volumes={
        "/host/skills": "/skills:ro",  # Read-only
        "/host/workspace": "/workspace",  # Read-write
    }
)

# Skills can't be modified by container
```

#### Anti-Pattern: Mounting Docker Socket

**✗ Wrong (dangerous)**:
```python
docker = DockerBackend(
    volumes={
        "/var/run/docker.sock": "/var/run/docker.sock",  # Container can control Docker!
    }
)

# Container has full Docker control - can break isolation
```

**✓ Correct**:
```python
# Don't mount Docker socket unless absolutely necessary
# Use separate orchestration for container management
```

---


---

**Navigation**: [⬅️ Part 5: Implementation](part5-implementation.md) | [Index](INDEX.md) | [Part 7: Migration & Troubleshooting ➡️](part7-migration-troubleshooting.md)
