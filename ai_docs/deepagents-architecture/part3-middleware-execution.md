# DeepAgents CLI vs SDK Architecture - Part 3: Middleware & Execution

> **Navigation**: [⬅️ Part 2: Core Concepts](part2-core-concepts.md) | [Index](INDEX.md) | [Part 4: Skills & Decision ➡️](part4-skills-decision.md)

**Sections**: 6-7 | Middleware Comparison, Execution Mechanisms

---

## 6. Middleware Comparison

This section compares the key middleware implementations in the DeepAgents SDK and discusses when to use each.

### 6.1 Middleware Overview

Middleware in DeepAgents follows the LangChain v1.0 middleware pattern:

```python
class Middleware:
    def before_model(self, state: AgentState) -> dict | None:
        """Called before model invocation."""
        pass

    def after_model(self, state: AgentState) -> dict | None:
        """Called after model invocation."""
        pass

    def modify_tools(self, tools: list) -> list:
        """Modify available tools."""
        return tools
```

Execution flow:
```
User Request
    ↓
[before_model] M1 → M2 → M3 → M4
    ↓
Model Invocation
    ↓
[after_model] M4 → M3 → M2 → M1 (reversed)
    ↓
Tool Execution
    ↓
Response
```

### 6.2 FilesystemMiddleware

**Purpose**: Generate file operation tools from backend capabilities.

**Responsibilities**:
1. Tool generation based on backend protocol
2. Tool call interception and routing
3. Execute tool generation (if backend supports execution)

#### Generated Tools

```python
# From FilesystemBackendProtocol
ls(path: str) -> list[str]
read_file(path: str) -> str
write_file(path: str, content: str) -> None
edit_file(path: str, old_content: str, new_content: str) -> None
glob(pattern: str) -> list[str]
grep(pattern: str, path: str) -> str

# From SandboxBackendProtocol
execute(command: str, workdir: str = None) -> str
```

#### Configuration

```python
from deepagents.middleware.filesystem import FilesystemMiddleware

middleware = FilesystemMiddleware(
    backend=backend_factory  # Lambda that creates backend with runtime
)
```

#### Tool Generation Logic

```python
# Simplified version of FilesystemMiddleware.modify_tools()

def modify_tools(self, tools):
    backend = self.backend_factory(runtime)

    # Check backend capabilities
    if hasattr(backend, 'read_file'):
        tools.append(create_read_file_tool(backend))

    if hasattr(backend, 'write_file'):
        tools.append(create_write_file_tool(backend))

    if hasattr(backend, 'ls'):
        tools.append(create_ls_tool(backend))

    if hasattr(backend, 'execute'):
        tools.append(create_execute_tool(backend))

    return tools
```

#### Backend Routing

```python
# Tool call flow
agent calls: read_file("/workspace/config.json")
    ↓
FilesystemMiddleware intercepts tool call
    ↓
Routes to backend: backend.read_file("/workspace/config.json")
    ↓
Backend resolves (CompositeBackend or direct)
    ↓
Result returned to agent
```

#### Usage Example

```python
backend_factory = lambda rt: CompositeBackend(
    default=DockerBackend(...),
    routes={
        "/workspace/": FilesystemBackend(...),
    }
)

middleware = [
    FilesystemMiddleware(backend=backend_factory),
    # Other middleware...
]

agent = create_agent(model, middleware=middleware, tools=[])

# Agent now has tools: ls, read_file, write_file, edit_file, glob, grep, execute
```

### 6.3 SkillsMiddleware

**Purpose**: Automatic skill discovery and documentation injection.

**Responsibilities**:
1. Scan skill directories for SKILL.md files
2. Parse skill metadata (name, description)
3. Inject skill documentation using progressive disclosure
4. Update agent system prompt with available skills

#### Configuration

```python
from deepagents.middleware.skills import SkillsMiddleware

middleware = SkillsMiddleware(
    backend=backend_factory,           # Backend for file operations
    sources=["/skills/", "/custom/"]   # Directories to scan
)
```

#### Discovery Process

```python
# Simplified discovery flow

def before_model(self, state):
    backend = self.backend_factory(runtime)

    # 1. Scan each source directory
    for source in self.sources:
        entries = backend.ls(source)

        for entry in entries:
            skill_path = f"{source}{entry}/SKILL.md"

            # 2. Read SKILL.md if exists
            try:
                content = backend.read_file(skill_path)

                # 3. Parse frontmatter
                metadata = parse_yaml_frontmatter(content)
                name = metadata['name']
                description = metadata['description']

                # 4. Store skill info
                skills[name] = {
                    'path': skill_path,
                    'description': description
                }
            except FileNotFoundError:
                continue

    # 5. Inject into system prompt
    skills_text = "\n".join([
        f"- {name}: {info['description']}"
        for name, info in skills.items()
    ])

    state['system_prompt'] += f"\n\n<available_skills>\n{skills_text}\n</available_skills>"

    return state
```

#### Progressive Disclosure Levels

**Level 1: Startup** (~100 tokens total)
```
<available_skills>
- file-hash: Calculate cryptographic hashes (MD5, SHA256, SHA512) of files.
- data-analysis: Analyze datasets and generate statistical reports.
- web-scraper: Extract structured data from web pages.
</available_skills>
```

**Level 2: On-Demand** (~5000 tokens per skill)
- Agent sees skill is relevant
- Middleware injects full SKILL.md content
- Includes usage instructions, examples

**Level 3: Execution** (as needed)
- Agent reads skill scripts using `read_file()`
- Agent executes skill scripts using `execute()`

#### Integration with FilesystemMiddleware

```python
middleware = [
    SkillsMiddleware(
        backend=backend_factory,
        sources=["/skills/"]
    ),
    FilesystemMiddleware(backend=backend_factory),
]

# Flow:
# 1. SkillsMiddleware discovers skills at startup
# 2. Injects skill list into system prompt
# 3. Agent sees skills in <available_skills> tag
# 4. Agent uses read_file() (from FilesystemMiddleware) to read skill documentation
# 5. Agent uses execute() (from FilesystemMiddleware) to run skill scripts
```

#### Custom Skills Directory Structure

```
skills/
├── file-hash/
│   ├── SKILL.md
│   └── scripts/
│       └── hash_file.py
├── data-analysis/
│   ├── SKILL.md
│   ├── scripts/
│   │   ├── analyze.py
│   │   └── visualize.py
│   └── references/
│       └── examples.md
└── web-scraper/
    ├── SKILL.md
    └── scripts/
        └── scrape.py
```

**Sources Configuration**:
```python
SkillsMiddleware(
    backend=backend_factory,
    sources=[
        "/skills/",           # Default skills
        "/custom-skills/",    # Custom skills
        "/team-skills/",      # Team-shared skills
    ]
)
```

### 6.4 SubAgentMiddleware

**Purpose**: Enable task delegation to specialized sub-agents.

**Responsibilities**:
1. Provide `task()` tool for delegation
2. Manage sub-agent creation and lifecycle
3. Stream sub-agent events (optional)
4. Support specialized sub-agent types

#### Configuration

```python
from langchain.agents.middleware import SubAgentMiddleware

middleware = SubAgentMiddleware(
    default_model=model,                     # Model for sub-agents
    default_tools=[],                        # Tools for general-purpose sub-agent
    subagents=[],                            # Specialized sub-agents
    include_general_purpose=True,            # Include general-purpose sub-agent
    stream_subagent_events=False,            # Stream tool calls from sub-agents
    default_middleware=[...],                # Middleware stack for sub-agents
)
```

#### Generated Tool

```python
task(
    instructions: str,      # Task description for sub-agent
    agent_type: str = "general-purpose"  # Which sub-agent to use
) -> str
```

#### Sub-Agent Types

**General-Purpose Sub-Agent**:
- Inherits all tools from parent agent
- Same middleware stack (configurable)
- Used for complex multi-step tasks

**Specialized Sub-Agents**:
```python
subagents=[
    {
        "name": "data-analyst",
        "description": "Analyze datasets and generate reports",
        "tools": [custom_analysis_tool],
        "middleware": [AnalysisMiddleware()],
    },
    {
        "name": "code-reviewer",
        "description": "Review code for best practices and bugs",
        "tools": [code_analysis_tool],
        "middleware": [CodeReviewMiddleware()],
    },
]
```

#### Event Streaming

```python
# Enable sub-agent event streaming
middleware = SubAgentMiddleware(
    stream_subagent_events=True,
    output_handlers=[console_handler, log_handler],
    ...
)

# Events emitted:
# - sub_agent_start: When sub-agent begins
# - sub_agent_tool_call: When sub-agent calls tool
# - sub_agent_tool_result: When tool returns
# - sub_agent_end: When sub-agent completes
```

#### Usage Example

```python
# Parent agent delegates complex task to sub-agent
agent: "I need to analyze this dataset and generate a report"
    ↓
Parent agent calls: task(
    instructions="Analyze dataset.csv and generate statistical report with visualizations",
    agent_type="general-purpose"
)
    ↓
SubAgentMiddleware creates sub-agent
    ↓
Sub-agent executes:
    - read_file("dataset.csv")
    - execute("python analyze.py dataset.csv")
    - write_file("report.md", report_content)
    ↓
Sub-agent returns results
    ↓
Parent agent receives results and responds to user
```

### 6.5 TodoListMiddleware

**Purpose**: Provide task tracking and management tools.

**Generated Tools**:
```python
add_todo(title: str, description: str = "") -> None
complete_todo(title: str) -> None
list_todos() -> list[dict]
update_todo(title: str, new_title: str = None, new_description: str = None) -> None
```

**Usage**:
```python
from langchain.agents.middleware import TodoListMiddleware

middleware = [
    TodoListMiddleware(),
    # Other middleware...
]

# Agent can now manage todos:
# - add_todo("Implement authentication", "Add JWT-based auth")
# - complete_todo("Implement authentication")
# - list_todos()
```

### 6.6 SummarizationMiddleware

**Purpose**: Automatic conversation summarization to manage context length.

**Configuration**:
```python
from langchain.agents.middleware import SummarizationMiddleware

middleware = SummarizationMiddleware(
    model=model,                          # Model for summarization
    max_tokens_before_summary=170000,     # Trigger threshold
    messages_to_keep=6,                   # Recent messages to preserve
)
```

**Behavior**:
- Monitors conversation token count
- When threshold exceeded, summarizes old messages
- Keeps recent messages in full detail
- Injects summary as system message

### 6.7 ShellMiddleware (Not in SDK)

**Purpose**: Provide direct shell access (similar to CLI approach).

**Note**: ShellMiddleware is a conceptual middleware that would provide CLI-like bash access in SDK agents. It's not part of the standard SDK but can be implemented as custom middleware.

**Hypothetical Implementation**:
```python
class ShellMiddleware:
    """Provides direct shell execution on host system."""

    def modify_tools(self, tools):
        tools.append(create_bash_tool())
        return tools

def create_bash_tool():
    def bash(command: str, description: str = "") -> str:
        """Execute bash command on host system."""
        import subprocess
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True
        )
        return result.stdout if result.returncode == 0 else result.stderr

    return bash
```

**When to Use ShellMiddleware**:
- Development environments where sandboxing is not required
- Trusted commands only
- Need direct host access for specific tools

**Security Warning**: ShellMiddleware bypasses sandboxing and executes commands directly on host. Use only in trusted environments.

### 6.8 Middleware Comparison Table

| Middleware | Purpose | Generated Tools | Backend Dependency |
|------------|---------|----------------|-------------------|
| FilesystemMiddleware | File operations | ls, read_file, write_file, edit_file, glob, grep, execute | Yes (requires backend factory) |
| SkillsMiddleware | Skill discovery | None (modifies system prompt) | Yes (for reading SKILL.md files) |
| SubAgentMiddleware | Task delegation | task() | No (creates sub-agents) |
| TodoListMiddleware | Task tracking | add_todo, complete_todo, list_todos, update_todo | No |
| SummarizationMiddleware | Context management | None (summarizes messages) | No |
| ShellMiddleware (custom) | Direct shell access | bash() | No |

### 6.9 Middleware Ordering

Order matters! Middleware executes in the order listed:

```python
middleware = [
    TodoListMiddleware(),         # 1. Task tracking (first)
    SkillsMiddleware(...),        # 2. Skill discovery
    FilesystemMiddleware(...),    # 3. File operations
    SubAgentMiddleware(...),      # 4. Task delegation
    SummarizationMiddleware(...), # 5. Summarization (late)
]
```

**Reasoning**:
1. **TodoListMiddleware first** - Todos should be available to all other middleware
2. **SkillsMiddleware early** - Skills should be discovered before file operations
3. **FilesystemMiddleware before SubAgent** - Sub-agents should inherit file tools
4. **SummarizationMiddleware late** - Summarize after all modifications

---

## 7. Execution Mechanisms

This section compares how commands are executed in CLI vs SDK approaches.

### 7.1 CLI Execution: bash Tool

In CLI approach, the agent has a `bash` tool that executes commands directly on the host system.

#### bash Tool Signature

```python
bash(
    command: str,           # Shell command to execute
    description: str,       # Human-readable description
    timeout: int = 120000   # Timeout in milliseconds
) -> str
```

#### Execution Flow

```
Agent decides to run command
    ↓
bash(command="python script.py", description="Run analysis script")
    ↓
CLI application receives tool call
    ↓
Execute on host: subprocess.run(["bash", "-c", "python script.py"])
    ↓
Capture stdout/stderr
    ↓
Return result to agent
```

#### Characteristics

- **Direct execution**: No isolation or sandboxing
- **Full shell features**: Pipes, redirects, environment variables
- **Host privileges**: Runs with user's permissions
- **Working directory**: Current directory of CLI application

#### Example Usage

```python
# Agent tool call
bash(
    command="find . -name '*.py' | xargs grep 'TODO'",
    description="Find all TODO comments in Python files"
)

# Executes directly on host
# Output: List of files with TODO comments
```

### 7.2 SDK Execution: execute Tool

In SDK approach, the agent has an `execute` tool generated by FilesystemMiddleware from backend capabilities.

#### execute Tool Signature

```python
execute(
    command: str,              # Command to execute
    workdir: str = None        # Working directory (optional)
) -> str
```

#### Execution Flow

```
Agent decides to run command
    ↓
execute(command="python script.py", workdir="/workspace")
    ↓
FilesystemMiddleware intercepts tool call
    ↓
Routes to backend
    ↓
Backend executes (DockerBackend, RemoteBackend, etc.)
    ↓
Result returned through layers
    ↓
Agent receives result
```

#### Backend-Specific Execution

**DockerBackend**:
```
execute("python script.py")
    ↓
docker exec <container_name> bash -c "python script.py"
    ↓
Runs in isolated container
    ↓
Result captured from container
```

**RemoteBackend**:
```
execute("python script.py")
    ↓
SSH connection to remote server
    ↓
ssh user@server "cd /workspace && python script.py"
    ↓
Result returned over network
```

**FilesystemBackend**:
- FilesystemBackend does NOT support execute
- Only file operations (read/write/ls)

#### Working Directory Handling

```python
# Specify working directory
execute("python script.py", workdir="/workspace/subdir")

# Backend resolves working directory:
# DockerBackend: cd /workspace/subdir && python script.py
# RemoteBackend: ssh user@server "cd /workspace/subdir && python script.py"
```

#### Example Usage

```python
# Agent tool call
execute(
    command="python /workspace/analysis.py --input data.csv",
    workdir="/workspace"
)

# Routed to DockerBackend
# Executed in container: docker exec agent-sandbox bash -c "cd /workspace && python ..."
# Container has /workspace mounted from host
# Output returned to agent
```

### 7.3 Execution Comparison

| Aspect | CLI bash Tool | SDK execute Tool |
|--------|--------------|-----------------|
| **Isolation** | None | Full (Docker/Remote) |
| **Where it runs** | Host system | Backend-dependent |
| **Shell features** | Full (pipes, redirects) | Full (backend-dependent) |
| **Working directory** | CLI's cwd | Configurable per call |
| **Permissions** | User's permissions | Container/Remote permissions |
| **Overhead** | Low (~0ms) | Medium (10-50ms for Docker) |
| **Security** | Trusts agent | Sandboxed |

### 7.4 Working Directory Concepts

#### CLI Working Directory

```bash
# CLI starts in: /Users/user/project
$ claude-code

# Agent executes:
bash("ls")  # Lists /Users/user/project
bash("cd subdir && ls")  # Lists /Users/user/project/subdir
bash("pwd")  # Output: /Users/user/project

# Working directory persists between bash calls
bash("cd /tmp")
bash("pwd")  # Output: /tmp
```

**Characteristics**:
- Persistent across commands (shell session state)
- Can change with `cd`
- Initially set to CLI's starting directory

#### SDK Working Directory

**DockerBackend**:
```python
backend = DockerBackend(
    workdir="/workspace",  # Default working directory in container
    ...
)

# Agent executes:
execute("pwd")  # Output: /workspace
execute("ls")   # Lists /workspace
execute("cd /tmp && pwd")  # Output: /tmp (but doesn't persist)
execute("pwd")  # Output: /workspace (back to default)
```

**Characteristics**:
- Default set by backend configuration
- Can override per execute() call
- Does NOT persist between calls (each command is isolated)

**Per-Call Override**:
```python
execute("ls", workdir="/workspace/subdir")  # Lists /workspace/subdir
execute("ls", workdir="/skills")            # Lists /skills
execute("ls")                               # Lists /workspace (default)
```

### 7.5 Path Resolution in CompositeBackend

CompositeBackend routes operations based on path prefixes:

```python
backend = CompositeBackend(
    default=DockerBackend(workdir="/workspace", ...),
    routes={
        "/skills/": FilesystemBackend(root_dir="/host/skills", virtual_mode=True),
        "/workspace/": FilesystemBackend(root_dir="/host/workspace", virtual_mode=True),
    }
)
```

#### File Operation Routing

```
read_file("/skills/hash/SKILL.md")
    ↓
Path starts with "/skills/"
    ↓
Route to: FilesystemBackend (fast host read)
    ↓
Maps to physical: /host/skills/hash/SKILL.md
    ↓
Read from host filesystem
```

```
read_file("/workspace/config.json")
    ↓
Path starts with "/workspace/"
    ↓
Route to: FilesystemBackend (fast host read)
    ↓
Maps to physical: /host/workspace/config.json
    ↓
Read from host filesystem
```

#### Execute Routing

```
execute("python /skills/hash/script.py /workspace/data.txt")
    ↓
execute() is NOT a file operation
    ↓
No route matches → fall to default backend
    ↓
DockerBackend.execute(...)
    ↓
docker exec agent-sandbox python /skills/hash/script.py /workspace/data.txt
    ↓
Container has both /skills and /workspace mounted
    ↓
Script runs in container with access to both directories
```

**Key Insight**: File reads are fast (routed to host), but execution is sandboxed (Docker). Volume mounts bridge the gap.

### 7.6 Shell Features Comparison

#### CLI bash Tool

Supports all shell features:
```python
# Pipes
bash("cat file.txt | grep pattern | sort")

# Redirects
bash("echo 'data' > output.txt")
bash("python script.py 2>&1 | tee log.txt")

# Environment variables
bash("export VAR=value && python script.py")

# Command substitution
bash("echo $(date +%Y-%m-%d)")

# Multiple commands
bash("cd /tmp && ls && pwd")
```

#### SDK execute Tool

Supports shell features through backend:

```python
# Pipes
execute("cat file.txt | grep pattern | sort")

# Redirects
execute("echo 'data' > output.txt")

# Environment variables (depends on backend)
execute("export VAR=value && python script.py")

# Multiple commands
execute("cd /tmp && ls && pwd")
```

**Backend-Specific Behavior**:
- **DockerBackend**: Full shell support (executes in bash)
- **RemoteBackend**: Full shell support (executes via SSH)
- **Custom backends**: Depends on implementation

### 7.7 Environment Variables

#### CLI Approach

```python
# CLI inherits user's environment
bash("echo $HOME")  # Output: /Users/user
bash("echo $PATH")  # Output: /usr/local/bin:/usr/bin:...

# Can set environment for single command
bash("MYVAR=value python script.py")
```

#### SDK Approach

```python
# DockerBackend with environment configuration
backend = DockerBackend(
    environment={
        "PYTHONUNBUFFERED": "1",
        "API_KEY": "secret",
    },
    ...
)

# Environment persists for all execute() calls in container
execute("echo $PYTHONUNBUFFERED")  # Output: 1
execute("python script.py")        # Script sees API_KEY
```

### 7.8 Execution Isolation Comparison

#### CLI Execution (No Isolation)

```
┌─────────────────────────────────────────┐
│          Host System                     │
│                                          │
│  CLI Process                             │
│      ↓                                   │
│  subprocess (bash)                       │
│      ↓                                   │
│  Python script (full host access)       │
│                                          │
│  - Can access all host files            │
│  - Can modify system                    │
│  - Can make network connections         │
│  - Full permissions                     │
└─────────────────────────────────────────┘
```

#### SDK Execution (Docker Isolation)

```
┌─────────────────────────────────────────┐
│          Host System                     │
│                                          │
│  ┌───────────────────────────────────┐  │
│  │  Docker Container                 │  │
│  │                                   │  │
│  │  execute() → bash                 │  │
│  │      ↓                            │  │
│  │  Python script (limited access)  │  │
│  │                                   │  │
│  │  - Only mounted volumes           │  │
│  │  - Isolated network               │  │
│  │  - Limited resources              │  │
│  │  - Container permissions only     │  │
│  └───────────────────────────────────┘  │
│                                          │
│  Mounted: /workspace/, /skills/          │
└─────────────────────────────────────────┘
```

---


---

**Navigation**: [⬅️ Part 2: Core Concepts](part2-core-concepts.md) | [Index](INDEX.md) | [Part 4: Skills & Decision ➡️](part4-skills-decision.md)
