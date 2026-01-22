# DeepAgents CLI vs SDK Architecture - Part 2: Core Concepts

> **Navigation**: [⬅️ Part 1: Overview](part1-overview.md) | [Index](INDEX.md) | [Part 3: Middleware & Execution ➡️](part3-middleware-execution.md)

**Sections**: 4-5 | Core Concepts, Backend Implementations Deep Dive

---

## 4. Core Concepts

### 4.1 Backend Types

Backends define **where and how** agent operations execute. The SDK supports multiple backend types that can be composed together.

#### 4.1.1 StateBackend

**Purpose**: Manages agent conversation state (messages, metadata, checkpoints).

**Responsibilities**:
- Store conversation history
- Manage agent state transitions
- Support checkpointing and time-travel

**When to Use**:
- Every agent needs a StateBackend (required for LangChain agent)
- Usually created automatically by `create_agent()`

**Implementation**:
```python
from deepagents.backends import StateBackend

# Created automatically with runtime reference
backend = StateBackend(runtime=runtime)

# StateBackend is NOT used for file operations or execution
# It only handles agent state (messages, checkpoints)
```

**Key Characteristics**:
- Always in-memory
- Lifecycle tied to agent runtime
- Not used for user-facing operations
- Required by LangChain StateGraph

#### 4.1.2 FilesystemBackend

**Purpose**: Provides file operations (read/write/ls/glob) on a specific directory.

**Responsibilities**:
- File I/O operations
- Directory listing
- Pattern matching (glob)
- Content search (grep)

**When to Use**:
- Fast host filesystem access
- Reading configuration files
- Reading skill definitions
- Accessing workspace files

**Implementation**:
```python
from deepagents.backends.filesystem import FilesystemBackend

backend = FilesystemBackend(
    root_dir="/host/workspace",  # Physical directory on host
    virtual_mode=True,           # Present as /workspace in agent
)

# Operations
backend.read_file("/workspace/config.json")  # Maps to /host/workspace/config.json
backend.write_file("/workspace/output.txt", "data")
backend.ls("/workspace/")
```

**Key Characteristics**:
- Direct host filesystem access (fast)
- No execution capability (read/write/ls only)
- Used for file operations, not command execution
- Commonly used in CompositeBackend routes

#### 4.1.3 DockerBackend

**Purpose**: Provides sandboxed execution environment using Docker containers.

**Responsibilities**:
- Command execution in Docker container
- Process isolation
- Resource limits
- Filesystem isolation with volume mounts

**When to Use**:
- Production deployments
- Untrusted code execution
- Security-critical applications
- Reproducible environments

**Implementation**:
```python
from deepagents.backends.docker import DockerBackend

backend = DockerBackend(
    image="python:3.11",
    container_name="agent-sandbox",
    workdir="/workspace",
    volumes={
        "/host/workspace": "/workspace",  # Mount host directory
        "/host/skills": "/skills",        # Mount skills directory
    },
    auto_start=True,  # Create/start container automatically
)

# Execute commands in container
backend.execute("python /workspace/script.py")
backend.execute("pip install requests")
```

**Key Characteristics**:
- Sandboxed execution (isolated from host)
- Requires Docker daemon
- Volume mounts for data sharing
- Startup overhead (container creation)
- Full execution capability (runs any command)

#### 4.1.4 RemoteBackend

**Purpose**: Executes operations on remote servers via SSH or API.

**Responsibilities**:
- Remote command execution
- Network file transfer
- Distributed computing

**When to Use**:
- Distributed agent systems
- Cloud execution
- High-performance computing
- Multi-machine workflows

**Implementation**:
```python
from deepagents.backends.remote import RemoteBackend

backend = RemoteBackend(
    host="remote-server.example.com",
    username="agent",
    ssh_key="/path/to/private_key",
    workdir="/remote/workspace",
)

# Execute on remote machine
backend.execute("python /remote/workspace/script.py")
```

**Key Characteristics**:
- Network-based execution
- SSH or API communication
- Latency considerations
- Requires remote server setup

#### 4.1.5 CompositeBackend

**Purpose**: Routes operations to different backends based on path prefixes.

**Responsibilities**:
- Path-based routing
- Backend composition
- Fallback to default backend

**When to Use**:
- Optimize performance (fast reads from host, execution in Docker)
- Mix backends (local files + remote execution)
- Skills + workspace separation

**Implementation**:
```python
from deepagents.backends.composite import CompositeBackend

backend = CompositeBackend(
    default=DockerBackend(...),  # Fallback for everything else
    routes={
        "/skills/": FilesystemBackend(root_dir="/host/skills", virtual_mode=True),
        "/workspace/": FilesystemBackend(root_dir="/host/workspace", virtual_mode=True),
    }
)

# Routing logic:
backend.read_file("/skills/hash/SKILL.md")      # → FilesystemBackend (fast)
backend.read_file("/workspace/config.json")     # → FilesystemBackend (fast)
backend.execute("python /skills/hash/script.py") # → DockerBackend (sandboxed)
```

**Key Characteristics**:
- Path-based dispatch
- Prefix matching (longest match wins)
- Falls back to default backend if no match
- Commonly used pattern: FilesystemBackend routes + DockerBackend default

### 4.2 Middleware Stack

Middleware provides composable functionality layers that intercept and modify agent behavior.

#### 4.2.1 Middleware Execution Order

```python
middleware_stack = [
    TodoListMiddleware(),        # 1. Executes first
    SkillsMiddleware(...),       # 2. Then this
    FilesystemMiddleware(...),   # 3. Then this
    SubAgentMiddleware(...),     # 4. Then this
]
```

Each middleware has hooks:
- `before_model(state)` - Before model invocation
- `after_model(state)` - After model invocation
- `modify_tools(tools)` - Modify available tools

Execution order:
```
User Request
    ↓
before_model: TodoList → Skills → Filesystem → SubAgent
    ↓
Model Invocation
    ↓
after_model: SubAgent → Filesystem → Skills → TodoList (reversed)
    ↓
Response
```

#### 4.2.2 FilesystemMiddleware

**Purpose**: Generates file operation tools and execute tool from backend capabilities.

**Responsibilities**:
- Tool generation (`ls`, `read_file`, `write_file`, etc.)
- Tool call interception and routing to backend
- Execute tool (if backend supports execution)

**Key Methods**:
```python
class FilesystemMiddleware:
    def modify_tools(self, tools):
        # Generate tools based on backend capabilities
        # - ls, read_file, write_file, edit_file, glob, grep
        # - execute (if backend has execute capability)
        pass

    def before_model(self, state):
        # Intercept file tool calls
        # Route to backend
        pass
```

**Usage**:
```python
FilesystemMiddleware(
    backend=backend_factory  # Lambda that creates backend with runtime
)
```

#### 4.2.3 SkillsMiddleware

**Purpose**: Discovers skills and injects documentation into agent context.

**Responsibilities**:
- Scan skill directories for SKILL.md files
- Parse skill metadata (name, description)
- Inject skill documentation using progressive disclosure
- Update agent context with available skills

**Progressive Disclosure**:
1. **Level 1**: Load skill names and descriptions at startup (~100 tokens)
2. **Level 2**: Inject full SKILL.md when skill is relevant (~5000 tokens)
3. **Level 3**: Agent reads skill scripts/references as needed

**Usage**:
```python
SkillsMiddleware(
    backend=backend_factory,
    sources=["/skills/"]  # Paths to scan for skills
)
```

**Key Methods**:
```python
class SkillsMiddleware:
    def before_model(self, state):
        # Scan sources for SKILL.md files
        # Parse metadata
        # Inject into system prompt
        pass
```

#### 4.2.4 SubAgentMiddleware

**Purpose**: Enables task delegation to sub-agents.

**Responsibilities**:
- Provide `task()` tool for delegation
- Manage sub-agent lifecycle
- Stream sub-agent events (optional)
- Support specialized sub-agents

**Usage**:
```python
SubAgentMiddleware(
    default_model=model,
    default_tools=[],
    subagents=[],  # Custom specialized sub-agents
    include_general_purpose=True,
    default_middleware=[...]  # Middleware for sub-agents
)
```

**Generated Tool**:
```python
task(
    instructions="Complex multi-step task description",
    agent_type="general-purpose"  # Or custom sub-agent name
)
```

### 4.3 Skills System

Skills extend agent capabilities through:
1. **Structured documentation** (SKILL.md)
2. **Executable scripts** (Python, bash, etc.)
3. **Reference materials** (docs, examples)

#### Skill Directory Structure

```
skills/
├── file-hash/
│   ├── SKILL.md                 # Required: metadata + instructions
│   └── scripts/
│       └── hash_file.py         # Executable script
├── data-analysis/
│   ├── SKILL.md
│   ├── scripts/
│   │   └── analyze.py
│   └── references/
│       └── examples.md          # Reference documentation
```

#### SKILL.md Format

```yaml
---
name: file-hash
description: Calculate cryptographic hashes (MD5, SHA256, SHA512) of files.
---

# File Hash Calculation

This skill computes cryptographic hashes of files using Python's hashlib.

## Usage

```bash
python /skills/file-hash/scripts/hash_file.py <file_path> <algorithm>
```

## Algorithms

- md5
- sha256
- sha512

## Example

```bash
python /skills/file-hash/scripts/hash_file.py /workspace/document.pdf sha256
```
```

#### Skills Discovery Flow

```
Agent Startup
    ↓
SkillsMiddleware.before_model()
    ↓
Scan sources=["/skills/"]
    ↓
backend.ls("/skills/") → [" file-hash", "data-analysis"]
    ↓
For each directory:
    backend.read_file("/skills/file-hash/SKILL.md")
    ↓
    Parse YAML frontmatter
    ↓
    Extract name + description
    ↓
Inject into system prompt:
    <available_skills>
    - file-hash: Calculate cryptographic hashes...
    - data-analysis: Analyze datasets...
    </available_skills>
    ↓
Agent receives context with skill list
```

### 4.4 Tool Discovery

#### CLI Tool Discovery

CLI tools are fixed and defined by the CLI implementation:
```
bash, read, write, edit, glob, grep, task, ...
```

No dynamic discovery - tools are hard-coded.

#### SDK Tool Discovery

SDK tools are generated dynamically based on:

1. **Backend Capabilities**:
```python
# FilesystemMiddleware checks backend protocol
if hasattr(backend, 'read_file'):
    tools.append(create_read_file_tool(backend))

if hasattr(backend, 'execute'):
    tools.append(create_execute_tool(backend))
```

2. **Middleware Contributions**:
```python
# Each middleware can add tools
class CustomMiddleware:
    def modify_tools(self, tools):
        tools.append(my_custom_tool)
        return tools
```

3. **Protocol-Based Detection**:
```python
from deepagents.backends.protocol import SandboxBackendProtocol

# Check if backend supports execution
if isinstance(backend, SandboxBackendProtocol):
    # Backend can execute commands
    tools.append(execute_tool)
```

#### Tool Generation Example

```python
# FilesystemMiddleware generates tools from backend

backend = CompositeBackend(
    default=DockerBackend(...),  # Has execute capability
    routes={
        "/workspace/": FilesystemBackend(...)  # Has read/write
    }
)

# FilesystemMiddleware inspects backend:
# - CompositeBackend has read_file, write_file, ls, glob, grep
# - Default backend (DockerBackend) has execute
#
# Generated tools:
# - ls(path)
# - read_file(path)
# - write_file(path, content)
# - edit_file(path, old, new)
# - glob(pattern)
# - grep(pattern, path)
# - execute(command, workdir)  # From DockerBackend
```

---

## 5. Backend Implementations Deep Dive

This section provides detailed coverage of all backend types, including implementation patterns, configuration options, and best practices.

### 5.1 StateBackend Deep Dive

#### Purpose and Responsibilities

StateBackend is a special backend that manages agent conversation state. Unlike other backends (which handle file operations or execution), StateBackend stores:

- **Message history** - All AI messages and tool calls
- **Checkpoints** - State snapshots for time-travel debugging
- **Metadata** - Custom state fields and agent configuration

#### Lifecycle

```python
# StateBackend is created automatically by create_agent()
from langchain.agents import create_agent

agent = create_agent(
    model=model,
    system_prompt="...",
    tools=[],
    middleware=middleware_stack
)

# Internally, create_agent() does:
# 1. Create runtime context
# 2. Create StateBackend(runtime=runtime)
# 3. Build LangGraph StateGraph with StateBackend
```

#### When You Need Manual StateBackend Creation

Most of the time, you never create StateBackend directly. However, you need it when:

1. **Using CompositeBackend** - Must pass StateBackend explicitly
2. **Custom state management** - Need custom checkpoint store

```python
# Example: CompositeBackend with explicit StateBackend
backend_factory = lambda rt: CompositeBackend(
    default=DockerBackend(...),
    state_backend=StateBackend(runtime=rt),  # Explicit state backend
    routes={...}
)
```

#### Key Characteristics

- **In-memory only** - State is not persisted to disk (unless using custom checkpoint store)
- **Runtime-bound** - Tied to agent runtime lifecycle
- **Not user-facing** - Agent developer doesn't interact with it directly
- **Required** - Every agent must have a StateBackend

### 5.2 FilesystemBackend Deep Dive

#### Purpose

FilesystemBackend provides file operations on a host directory with optional path virtualization.

#### Configuration Options

```python
from deepagents.backends.filesystem import FilesystemBackend

backend = FilesystemBackend(
    root_dir="/host/workspace",   # Physical directory on host
    virtual_mode=True,             # Present as virtual path
    virtual_prefix="/workspace",   # Virtual path prefix (if virtual_mode=True)
    read_only=False,               # Allow writes
)
```

#### Virtual Mode Explained

**Virtual Mode OFF** (`virtual_mode=False`):
```python
backend = FilesystemBackend(root_dir="/host/workspace", virtual_mode=False)

# Paths are physical
backend.read_file("/host/workspace/file.txt")  # ✓ Works
backend.read_file("/workspace/file.txt")       # ✗ Fails (no such file)
```

**Virtual Mode ON** (`virtual_mode=True`):
```python
backend = FilesystemBackend(
    root_dir="/host/workspace",
    virtual_mode=True,
    virtual_prefix="/workspace"
)

# Paths are virtual
backend.read_file("/workspace/file.txt")       # ✓ Maps to /host/workspace/file.txt
backend.read_file("/host/workspace/file.txt")  # ✗ Fails (path doesn't match prefix)
```

#### Common Usage Patterns

**Pattern 1: Direct Host Access (No Virtualization)**
```python
backend = FilesystemBackend(root_dir="/home/user/project", virtual_mode=False)
# Agent sees actual host paths: /home/user/project/
```

**Pattern 2: Virtual Workspace**
```python
backend = FilesystemBackend(
    root_dir="/home/user/agent-workspace",
    virtual_mode=True,
    virtual_prefix="/workspace"
)
# Agent sees: /workspace/
# Actually reads from: /home/user/agent-workspace/
```

**Pattern 3: CompositeBackend Routes**
```python
composite = CompositeBackend(
    default=DockerBackend(...),
    routes={
        "/skills/": FilesystemBackend(
            root_dir="/host/skills",
            virtual_mode=True
        ),
        "/workspace/": FilesystemBackend(
            root_dir="/host/workspace",
            virtual_mode=True
        ),
    }
)

# Agent path: /skills/hash/SKILL.md
# Routed to: FilesystemBackend (fast host read)
# Physical path: /host/skills/hash/SKILL.md
```

#### Capabilities

FilesystemBackend implements:
- `read_file(path)` - Read file contents
- `write_file(path, content)` - Write file
- `ls(path)` - List directory
- `glob(pattern)` - Pattern matching
- `grep(pattern, path)` - Search file contents

FilesystemBackend does NOT implement:
- `execute(command)` - No execution capability

#### Performance Characteristics

- **Very fast** - Direct filesystem access, no overhead
- **No isolation** - Operates on host filesystem directly
- **Use in CompositeBackend routes** - Fast reads for skill definitions, workspace files

### 5.3 DockerBackend Deep Dive

#### Purpose

DockerBackend provides sandboxed command execution inside Docker containers with controlled filesystem access.

#### Full Configuration

```python
from backends.docker_backend import DockerBackend

backend = DockerBackend(
    # Container configuration
    image="python:3.11",                    # Docker image to use
    container_name="agent-sandbox",         # Container name
    workdir="/workspace",                   # Working directory in container

    # Volume mounts (host_path: container_path)
    volumes={
        "/host/workspace": "/workspace",    # Mount workspace
        "/host/skills": "/skills",          # Mount skills
    },

    # Lifecycle
    auto_start=True,                        # Auto-create/start container
    auto_remove=False,                      # Keep container after agent stops

    # Environment variables
    environment={
        "PYTHONUNBUFFERED": "1",
        "CUSTOM_VAR": "value",
    },

    # Resource limits (optional)
    mem_limit="1g",                         # Memory limit
    cpu_quota=50000,                        # CPU quota (50% of one core)
)
```

#### Container Lifecycle

```
Agent Start
    ↓
DockerBackend.__init__(auto_start=True)
    ↓
Check if container exists
    ├─ Exists and running → Use it
    ├─ Exists but stopped → Start it
    └─ Doesn't exist → Create and start it
    ↓
backend.execute("command")
    ↓
docker exec <container_name> command
    ↓
Agent Stop
    ↓
Container behavior depends on auto_remove:
    ├─ auto_remove=True → docker rm <container>
    └─ auto_remove=False → Container keeps running
```

#### Volume Mounts Explained

Volume mounts enable the container to access host directories:

```python
volumes={
    "/host/workspace": "/workspace",  # Host → Container mapping
    "/host/skills": "/skills",
}

# What this means:
# - Files in /host/workspace/ on host are visible at /workspace/ in container
# - Files in /host/skills/ on host are visible at /skills/ in container
# - Changes inside container reflect on host (bidirectional)
```

**Example Flow**:
```python
# 1. Agent reads skill (via CompositeBackend route)
backend.read_file("/skills/hash/SKILL.md")
# → Routes to FilesystemBackend
# → Fast host read from /host/skills/hash/SKILL.md

# 2. Agent executes skill script
backend.execute("python /skills/hash/scripts/hash_file.py /workspace/doc.pdf sha256")
# → Routes to DockerBackend (default)
# → Executes in container: docker exec agent-sandbox python /skills/hash/...
# → Container has /skills/ mounted from /host/skills/
# → Script can access /workspace/doc.pdf (mounted from /host/workspace/)
```

#### Image Selection

**Option 1: Pre-built Images**
```python
# Python base image
image="python:3.11"

# Python with common packages
image="python:3.11-slim"

# Ubuntu with Python
image="ubuntu:22.04"  # Requires Python installation in Dockerfile
```

**Option 2: Custom Image**
```dockerfile
# Dockerfile
FROM python:3.11

RUN pip install requests numpy pandas

WORKDIR /workspace
```

```bash
# Build image
docker build -t skill-agent:latest .
```

```python
# Use custom image
backend = DockerBackend(
    image="skill-agent:latest",
    ...
)
```

#### Execution Methods

```python
# Simple command
result = backend.execute("python script.py")

# With working directory
result = backend.execute("python script.py", workdir="/workspace")

# Shell features (pipes, redirects)
result = backend.execute("cat file.txt | grep pattern > output.txt")

# Multi-line commands
result = backend.execute("""
python -c '
import sys
print(sys.version)
'
""")
```

#### Security Considerations

DockerBackend provides isolation but is not a complete security solution:

**Isolated**:
- Process isolation (container processes can't affect host)
- Filesystem isolation (except mounted volumes)
- Network isolation (optional)

**Not Isolated**:
- Mounted volumes are bidirectional (container can modify host files)
- Docker socket access (if mounted) gives container full control
- Resource limits must be explicitly configured

**Best Practices**:
```python
# 1. Use read-only volumes for sensitive data
volumes={
    "/host/skills": "/skills:ro",  # Read-only mount
}

# 2. Set resource limits
mem_limit="1g",
cpu_quota=50000,

# 3. Use unprivileged containers
privileged=False,

# 4. Limit network access (in Dockerfile)
# Use network_mode="none" in Docker configuration
```

#### Performance Characteristics

- **Startup overhead**: ~1-2 seconds for container creation
- **Execution overhead**: ~10-50ms per command (docker exec latency)
- **Filesystem overhead**: Native speed for mounted volumes
- **Memory overhead**: ~10-50MB base container memory

**Optimization Tips**:
1. **Reuse containers**: Use `auto_start=True` and `auto_remove=False`
2. **Keep containers warm**: Don't stop containers between requests
3. **Mount volumes**: Avoid copying files into container
4. **Use slim images**: Reduces image pull time and memory usage

### 5.4 CompositeBackend Deep Dive

#### Purpose

CompositeBackend routes operations to different backends based on path prefixes, enabling:
- **Performance optimization** - Fast host reads, sandboxed execution
- **Backend mixing** - Local files + remote execution
- **Logical separation** - Skills, workspace, temp directories

#### Architecture

```
CompositeBackend
├── default: Backend                  # Fallback for unmatched paths
├── state_backend: StateBackend       # Agent state management
└── routes: Dict[str, Backend]        # Path prefix → Backend mapping
```

#### Path Resolution Algorithm

```
Operation: backend.read_file("/workspace/config.json")
    ↓
CompositeBackend resolves path "/workspace/config.json"
    ↓
Check routes (longest prefix match):
    - "/workspace/" matches → Use FilesystemBackend
    - "/skills/" doesn't match
    ↓
Route to: FilesystemBackend(root_dir="/host/workspace")
    ↓
FilesystemBackend.read_file("/workspace/config.json")
    ↓
Maps to physical path: /host/workspace/config.json
    ↓
Result returned
```

```
Operation: backend.execute("python /workspace/script.py")
    ↓
CompositeBackend checks if operation is file operation
    ↓
execute() is NOT a file operation (it's execution)
    ↓
No route matches → Fall to default backend
    ↓
default = DockerBackend(...)
    ↓
DockerBackend.execute("python /workspace/script.py")
    ↓
Executes in container (which has /workspace mounted)
    ↓
Result returned
```

#### Configuration Patterns

**Pattern 1: Skills + Workspace + Docker Execution**
```python
backend = CompositeBackend(
    default=DockerBackend(
        image="python:3.11",
        container_name="agent-sandbox",
        workdir="/workspace",
        volumes={
            "/host/workspace": "/workspace",
            "/host/skills": "/skills",
        },
        auto_start=True,
    ),
    routes={
        "/skills/": FilesystemBackend(
            root_dir="/host/skills",
            virtual_mode=True
        ),
        "/workspace/": FilesystemBackend(
            root_dir="/host/workspace",
            virtual_mode=True
        ),
    }
)

# Flow:
# read_file("/skills/hash/SKILL.md") → FilesystemBackend (fast)
# read_file("/workspace/config.json") → FilesystemBackend (fast)
# execute("python /skills/hash/script.py") → DockerBackend (sandboxed)
```

**Pattern 2: Local Workspace + Remote Execution**
```python
backend = CompositeBackend(
    default=RemoteBackend(host="compute-server"),
    routes={
        "/workspace/": FilesystemBackend(root_dir="/local/workspace", virtual_mode=True),
    }
)

# Flow:
# read_file("/workspace/data.csv") → FilesystemBackend (local, fast)
# execute("python /workspace/train.py") → RemoteBackend (remote server)
```

**Pattern 3: Multi-Workspace**
```python
backend = CompositeBackend(
    default=DockerBackend(...),
    routes={
        "/project1/": FilesystemBackend(root_dir="/host/project1", virtual_mode=True),
        "/project2/": FilesystemBackend(root_dir="/host/project2", virtual_mode=True),
        "/shared/": FilesystemBackend(root_dir="/host/shared", virtual_mode=True),
    }
)
```

#### Routing Precedence

Routes are matched by **longest prefix**:

```python
routes={
    "/workspace/": FilesystemBackend(...),         # Priority 2
    "/workspace/subdir/": FilesystemBackend(...),  # Priority 1 (longer match)
}

# Path: /workspace/subdir/file.txt
# Matches both routes, chooses longer: /workspace/subdir/
```

#### Backend Factory Pattern

CompositeBackend requires a **runtime** reference for StateBackend:

```python
# Correct: Use lambda factory
backend_factory = lambda rt: CompositeBackend(
    default=DockerBackend(...),
    state_backend=StateBackend(runtime=rt),  # Runtime injected
    routes={...}
)

# Pass factory to middleware
FilesystemMiddleware(backend=backend_factory)
```

Why factory?
- StateBackend needs runtime reference
- Runtime is only available during agent execution
- Factory defers backend creation until runtime is available

#### State Backend Integration

```python
backend = CompositeBackend(
    default=DockerBackend(...),
    state_backend=StateBackend(runtime=rt),  # Explicit state backend
    routes={...}
)

# Agent state operations go to StateBackend
# File operations route based on path
# Execution operations go to default backend
```

Without explicit `state_backend`:
```python
backend = CompositeBackend(
    default=DockerBackend(...),
    # No state_backend specified
    routes={...}
)

# StateBackend is auto-created by create_agent()
# But CompositeBackend won't know about it
# May cause issues with state management
```

**Best Practice**: Always specify `state_backend` explicitly in CompositeBackend.

### 5.5 RemoteBackend Deep Dive

#### Purpose

RemoteBackend executes operations on remote servers, enabling:
- Distributed agent systems
- Cloud execution environments
- High-performance computing integration

#### Configuration

```python
from deepagents.backends.remote import RemoteBackend

backend = RemoteBackend(
    # Connection
    host="remote-server.example.com",
    port=22,
    username="agent",

    # Authentication (choose one)
    password="secret",                        # Password auth
    ssh_key="/path/to/private_key",          # Key-based auth

    # Working directory on remote
    workdir="/remote/workspace",

    # Connection options
    timeout=30,
    keepalive_interval=10,
)
```

#### Capabilities

RemoteBackend implements:
- `execute(command)` - Run commands on remote server
- `read_file(path)` - Read files via SFTP
- `write_file(path, content)` - Write files via SFTP
- `ls(path)` - List remote directory

#### Performance Considerations

- **Network latency**: 10-500ms per operation depending on location
- **File transfer**: Large file operations can be slow
- **Connection pooling**: Reuse SSH connections for multiple operations
- **Batch operations**: Combine multiple commands when possible

#### Use Cases

**Distributed Computing**:
```python
backend = CompositeBackend(
    default=RemoteBackend(host="gpu-server"),  # GPU-intensive tasks
    routes={
        "/workspace/": FilesystemBackend(...),  # Local data access
    }
)

# Data stays local, computation runs on GPU server
```

**Multi-Region Deployment**:
```python
backends = {
    "us-west": RemoteBackend(host="us-west.example.com"),
    "eu-central": RemoteBackend(host="eu-central.example.com"),
}

# Route to appropriate region based on user location
```

### 5.6 Custom Backend Implementation

You can implement custom backends by following the Backend Protocol:

```python
from deepagents.backends.protocol import SandboxBackendProtocol

class CustomBackend(SandboxBackendProtocol):
    """Custom backend implementation."""

    def __init__(self, config):
        self.config = config
        # Initialize your backend

    def execute(self, command: str, workdir: str = None) -> str:
        """Execute command in custom environment."""
        # Your implementation
        pass

    def read_file(self, path: str) -> str:
        """Read file from custom storage."""
        # Your implementation
        pass

    def write_file(self, path: str, content: str) -> None:
        """Write file to custom storage."""
        # Your implementation
        pass

    def ls(self, path: str) -> list[str]:
        """List directory in custom storage."""
        # Your implementation
        pass

    def cleanup(self) -> None:
        """Cleanup resources."""
        # Your implementation
        pass
```

#### Example: Custom Cloud Backend

```python
class S3Backend(SandboxBackendProtocol):
    """Backend that stores files in S3 and executes on Lambda."""

    def __init__(self, bucket_name, lambda_function):
        self.s3_client = boto3.client('s3')
        self.lambda_client = boto3.client('lambda')
        self.bucket = bucket_name
        self.lambda_function = lambda_function

    def read_file(self, path: str) -> str:
        """Read file from S3."""
        response = self.s3_client.get_object(
            Bucket=self.bucket,
            Key=path.lstrip('/')
        )
        return response['Body'].read().decode('utf-8')

    def write_file(self, path: str, content: str) -> None:
        """Write file to S3."""
        self.s3_client.put_object(
            Bucket=self.bucket,
            Key=path.lstrip('/'),
            Body=content.encode('utf-8')
        )

    def execute(self, command: str, workdir: str = None) -> str:
        """Execute command via Lambda."""
        response = self.lambda_client.invoke(
            FunctionName=self.lambda_function,
            InvocationType='RequestResponse',
            Payload=json.dumps({
                'command': command,
                'workdir': workdir
            })
        )
        result = json.loads(response['Payload'].read())
        return result['output']

    def ls(self, path: str) -> list[str]:
        """List S3 objects."""
        response = self.s3_client.list_objects_v2(
            Bucket=self.bucket,
            Prefix=path.lstrip('/')
        )
        return [obj['Key'] for obj in response.get('Contents', [])]

    def cleanup(self) -> None:
        """No cleanup needed for S3/Lambda."""
        pass
```

#### Backend Protocol Reference

**Required Methods**:
- `execute(command, workdir)` - For SandboxBackendProtocol
- `read_file(path)` - For file operations
- `write_file(path, content)` - For file operations
- `ls(path)` - For directory listing

**Optional Methods**:
- `glob(pattern)` - Pattern matching
- `grep(pattern, path)` - Content search
- `cleanup()` - Resource cleanup

**Protocol Inheritance**:
```
Backend (base protocol)
    ↓
FilesystemBackendProtocol (adds file operations)
    ↓
SandboxBackendProtocol (adds execute)
```

---


---

**Navigation**: [⬅️ Part 1: Overview](part1-overview.md) | [Index](INDEX.md) | [Part 3: Middleware & Execution ➡️](part3-middleware-execution.md)
