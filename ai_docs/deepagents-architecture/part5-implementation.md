# DeepAgents CLI vs SDK Architecture - Part 5: Implementation Patterns

> **Navigation**: [⬅️ Part 4: Skills & Decision](part4-skills-decision.md) | [Index](INDEX.md) | [Part 6: Comparison & Patterns ➡️](part6-comparison-patterns.md)

**Section**: 10 | Implementation Patterns (7 Complete Examples)

---

## 10. Implementation Patterns

This section provides concrete implementation examples for common patterns, progressing from minimal to full-featured setups.

### 10.1 Pattern 1: Minimal SDK (State Only)

**Use Case**: Structured agent code without execution capabilities.

**Implementation**:

```python
from langchain.agents import create_agent
from langchain_anthropic import ChatAnthropic

# Model
model = ChatAnthropic(model="claude-sonnet-4-5")

# System prompt
system_prompt = """You are a helpful assistant.
You can answer questions and provide information."""

# Create agent (minimal)
agent = create_agent(
    model=model,
    system_prompt=system_prompt,
    tools=[],        # No tools
    middleware=[],   # No middleware
)

# Run agent
result = agent.invoke({"messages": [{"role": "user", "content": "Hello!"}]})
print(result['messages'][-1]['content'])
```

**Characteristics**:
- No file operations
- No execution
- Pure conversation
- StateBackend automatically created

**When to Use**:
- Chatbots without file/command access
- Q&A systems
- Conversational interfaces

### 10.2 Pattern 2: Filesystem Access

**Use Case**: Agent needs to read/write files but not execute commands.

**Implementation**:

```python
from langchain.agents import create_agent
from langchain_anthropic import ChatAnthropic
from deepagents.backends.filesystem import FilesystemBackend
from deepagents.middleware.filesystem import FilesystemMiddleware
from pathlib import Path

# Model
model = ChatAnthropic(model="claude-sonnet-4-5")

# Backend: FilesystemBackend for file operations
workspace_path = Path("./workspace").resolve()

backend_factory = lambda rt: FilesystemBackend(
    root_dir=str(workspace_path),
    virtual_mode=True,
    virtual_prefix="/workspace"
)

# Middleware
middleware = [
    FilesystemMiddleware(backend=backend_factory)
]

# System prompt
system_prompt = """You are a file management assistant.
You can read, write, and organize files in the workspace."""

# Create agent
agent = create_agent(
    model=model,
    system_prompt=system_prompt,
    tools=[],
    middleware=middleware,
)

# Run agent
result = agent.invoke({
    "messages": [{"role": "user", "content": "List all files in the workspace"}]
})
```

**Generated Tools**:
- `ls(path)`
- `read_file(path)`
- `write_file(path, content)`
- `edit_file(path, old, new)`
- `glob(pattern)`
- `grep(pattern, path)`

**No execution** - FilesystemBackend doesn't support `execute()`

**When to Use**:
- File organization assistants
- Document processors (read-only or write-only)
- Configuration file managers

### 10.3 Pattern 3: Docker Execution (Sandboxed)

**Use Case**: Agent needs sandboxed command execution.

**Implementation**:

```python
from langchain.agents import create_agent
from langchain_anthropic import ChatAnthropic
from deepagents.backends.filesystem import FilesystemBackend
from deepagents.middleware.filesystem import FilesystemMiddleware
from backends.docker_backend import DockerBackend
from deepagents.backends.composite import CompositeBackend
from pathlib import Path

# Model
model = ChatAnthropic(model="claude-sonnet-4-5")

# Paths
workspace_path = Path("./workspace").resolve()

# Docker backend
docker_backend = DockerBackend(
    image="python:3.11",
    container_name="agent-sandbox",
    workdir="/workspace",
    volumes={
        str(workspace_path): "/workspace",
    },
    auto_start=True,
)

# Composite backend for optimal performance
backend_factory = lambda rt: CompositeBackend(
    default=docker_backend,  # Execution happens in Docker
    routes={
        "/workspace/": FilesystemBackend(  # Fast file reads from host
            root_dir=str(workspace_path),
            virtual_mode=True
        ),
    }
)

# Middleware
middleware = [
    FilesystemMiddleware(backend=backend_factory)
]

# System prompt
system_prompt = """You are a Python development assistant.
You can write and execute Python scripts in a sandboxed environment."""

# Create agent
agent = create_agent(
    model=model,
    system_prompt=system_prompt,
    tools=[],
    middleware=middleware,
)

# Run agent
result = agent.invoke({
    "messages": [{"role": "user", "content": "Create a Python script that prints 'Hello World' and run it"}]
})
```

**Generated Tools**:
- `ls(path)`
- `read_file(path)` - Fast (routes to FilesystemBackend)
- `write_file(path, content)` - Fast (routes to FilesystemBackend)
- `edit_file(path, old, new)`
- `glob(pattern)`
- `grep(pattern, path)`
- `execute(command, workdir)` - Sandboxed (routes to DockerBackend)

**When to Use**:
- Code execution agents
- Data processing with scripts
- Untrusted code execution
- Production deployments

### 10.4 Pattern 4: Docker + Skills

**Use Case**: Agent with sandboxed execution and domain-specific skills.

**Implementation**:

```python
from langchain.agents import create_agent
from langchain_anthropic import ChatAnthropic
from deepagents.backends.filesystem import FilesystemBackend
from deepagents.backends.composite import CompositeBackend
from deepagents.middleware.filesystem import FilesystemMiddleware
from deepagents.middleware.skills import SkillsMiddleware
from backends.docker_backend import DockerBackend
from pathlib import Path

# Model
model = ChatAnthropic(model="claude-sonnet-4-5")

# Paths
workspace_path = Path("./workspace").resolve()
skills_path = Path("./skills").resolve()

# Docker backend with volume mounts for both workspace and skills
docker_backend = DockerBackend(
    image="python:3.11",
    container_name="skill-agent-sandbox",
    workdir="/workspace",
    volumes={
        str(workspace_path): "/workspace",
        str(skills_path): "/skills",  # Skills accessible in container
    },
    auto_start=True,
)

# Composite backend
backend_factory = lambda rt: CompositeBackend(
    default=docker_backend,
    routes={
        "/workspace/": FilesystemBackend(root_dir=str(workspace_path), virtual_mode=True),
        "/skills/": FilesystemBackend(root_dir=str(skills_path), virtual_mode=True),
    }
)

# Middleware stack
middleware = [
    SkillsMiddleware(
        backend=backend_factory,
        sources=["/skills/"]  # Scan this directory for skills
    ),
    FilesystemMiddleware(backend=backend_factory),
]

# System prompt
system_prompt = """You are a versatile assistant with specialized skills.

## Available Skills

Skills are automatically discovered and listed in <available_skills> tag.

### How to Use Skills

1. Read skill documentation: read_file("/skills/skill-name/SKILL.md")
2. Follow skill instructions (usually involves executing scripts)
3. Execute skill scripts: execute("python /skills/skill-name/scripts/script.py ...")
"""

# Create agent
agent = create_agent(
    model=model,
    system_prompt=system_prompt,
    tools=[],
    middleware=middleware,
)

# Run agent
result = agent.invoke({
    "messages": [{"role": "user", "content": "Calculate the SHA-256 hash of document.pdf"}]
})
```

**Skills Directory**:
```
skills/
├── file-hash/
│   ├── SKILL.md
│   └── scripts/
│       └── hash_file.py
└── data-analysis/
    ├── SKILL.md
    └── scripts/
        └── analyze.py
```

**Execution Flow**:
1. SkillsMiddleware discovers skills at startup
2. Agent sees skill list in context
3. Agent reads skill documentation (fast - FilesystemBackend route)
4. Agent executes skill script (sandboxed - DockerBackend)

**When to Use**:
- Domain-specific agents (data science, web scraping, etc.)
- Reusable capabilities across agents
- Complex workflows requiring documentation

### 10.5 Pattern 5: Full-Featured (Docker + Skills + SubAgents)

**Use Case**: Production-ready agent with all features.

**Implementation**:

```python
from langchain.agents import create_agent
from langchain.agents.middleware import TodoListMiddleware, SummarizationMiddleware
from langchain_anthropic import ChatAnthropic
from langchain_anthropic.middleware import AnthropicPromptCachingMiddleware
from deepagents.backends.filesystem import FilesystemBackend
from deepagents.backends.composite import CompositeBackend
from deepagents.middleware.filesystem import FilesystemMiddleware
from deepagents.middleware.skills import SkillsMiddleware
from deepagents.middleware.patch_tool_calls import PatchToolCallsMiddleware
from backends.docker_backend import DockerBackend
from src.middleware import CustomSubAgentMiddleware
from pathlib import Path

def create_production_agent():
    """Create full-featured production agent."""

    # Model
    model = ChatAnthropic(model="claude-sonnet-4-5")

    # Paths
    workspace_path = Path("./workspace").resolve()
    skills_path = Path("./skills").resolve()

    # Docker backend
    docker_backend = DockerBackend(
        image="skill-agent:latest",  # Custom image with dependencies
        container_name="agent-sandbox",
        workdir="/workspace",
        volumes={
            str(workspace_path): "/workspace",
            str(skills_path): "/skills",
        },
        auto_start=True,
        mem_limit="1g",  # Resource limits
    )

    # Composite backend
    backend_factory = lambda rt: CompositeBackend(
        default=docker_backend,
        routes={
            "/workspace/": FilesystemBackend(root_dir=str(workspace_path), virtual_mode=True),
            "/skills/": FilesystemBackend(root_dir=str(skills_path), virtual_mode=True),
        }
    )

    # Full middleware stack
    middleware = [
        # Task tracking
        TodoListMiddleware(),

        # Skills discovery
        SkillsMiddleware(
            backend=backend_factory,
            sources=["/skills/"]
        ),

        # File operations
        FilesystemMiddleware(backend=backend_factory),

        # Task delegation
        CustomSubAgentMiddleware(
            default_model=model,
            default_tools=[],
            subagents=[],
            include_general_purpose=True,
            stream_subagent_events=True,  # Enable event streaming
            default_middleware=[
                TodoListMiddleware(),
                SkillsMiddleware(backend=backend_factory, sources=["/skills/"]),
                FilesystemMiddleware(backend=backend_factory),
                SummarizationMiddleware(model=model, max_tokens_before_summary=170000, messages_to_keep=6),
                AnthropicPromptCachingMiddleware(unsupported_model_behavior="ignore"),
                PatchToolCallsMiddleware(),
            ],
        ),

        # Conversation management
        SummarizationMiddleware(
            model=model,
            max_tokens_before_summary=170000,
            messages_to_keep=6,
        ),

        # Prompt caching
        AnthropicPromptCachingMiddleware(unsupported_model_behavior="ignore"),

        # Compatibility
        PatchToolCallsMiddleware(),
    ]

    # Comprehensive system prompt
    system_prompt = """You are an advanced AI assistant with comprehensive capabilities.

## Available Tools

You have access to:
- **File tools**: ls, read_file, write_file, edit_file, glob, grep
- **Execute tool**: Run commands in sandboxed Docker environment
- **Task tool**: Delegate complex multi-step tasks to sub-agents
- **Todo tools**: Track and manage tasks

## Skills

Skills are specialized capabilities discovered automatically. See <available_skills> tag.

### Using Skills

1. Read skill documentation: read_file("/skills/skill-name/SKILL.md")
2. Follow instructions in SKILL.md
3. Execute skill scripts: execute("python /skills/skill-name/scripts/script.py ...")

### Important Notes

- You CANNOT compute cryptographic hashes directly - use the file-hash skill
- You CANNOT process binary files directly - use appropriate skills
- Read skill documentation first before using skills
- Use task() tool for complex multi-step workflows

## Best Practices

- Break complex tasks into smaller steps
- Use todos to track progress
- Delegate complex workflows to sub-agents
- Always read skill documentation before using skills
"""

    # Create agent
    agent = create_agent(
        model=model,
        system_prompt=system_prompt,
        tools=[],
        middleware=middleware,
    )

    return agent

# Usage
agent = create_production_agent()

result = agent.invoke({
    "messages": [{"role": "user", "content": "Analyze the dataset and generate a report"}]
})
```

**Features**:
- ✓ Sandboxed execution (DockerBackend)
- ✓ Fast file operations (CompositeBackend routes)
- ✓ Automatic skills discovery (SkillsMiddleware)
- ✓ Task delegation (SubAgentMiddleware)
- ✓ Task tracking (TodoListMiddleware)
- ✓ Context management (SummarizationMiddleware)
- ✓ Prompt caching (AnthropicPromptCachingMiddleware)
- ✓ Event streaming (CustomSubAgentMiddleware)

**When to Use**:
- Production deployments
- Complex multi-step workflows
- Security-critical applications
- Multi-tenant systems

### 10.6 Pattern 6: Remote Execution

**Use Case**: Execute operations on remote servers.

**Implementation**:

```python
from langchain.agents import create_agent
from langchain_anthropic import ChatAnthropic
from deepagents.backends.remote import RemoteBackend
from deepagents.backends.composite import CompositeBackend
from deepagents.backends.filesystem import FilesystemBackend
from deepagents.middleware.filesystem import FilesystemMiddleware
from pathlib import Path

# Model
model = ChatAnthropic(model="claude-sonnet-4-5")

# Local workspace for fast file reads
workspace_path = Path("./workspace").resolve()

# Remote backend for execution
remote_backend = RemoteBackend(
    host="compute-server.example.com",
    username="agent",
    ssh_key="/path/to/private_key",
    workdir="/remote/workspace",
)

# Composite: local file reads, remote execution
backend_factory = lambda rt: CompositeBackend(
    default=remote_backend,  # Execute on remote
    routes={
        "/workspace/": FilesystemBackend(  # Read from local
            root_dir=str(workspace_path),
            virtual_mode=True
        ),
    }
)

# Middleware
middleware = [
    FilesystemMiddleware(backend=backend_factory)
]

# System prompt
system_prompt = """You are a distributed computing assistant.
You can access local files and execute commands on remote servers."""

# Create agent
agent = create_agent(
    model=model,
    system_prompt=system_prompt,
    tools=[],
    middleware=middleware,
)

# Run agent
result = agent.invoke({
    "messages": [{"role": "user", "content": "Run the training script on the remote server"}]
})
```

**When to Use**:
- High-performance computing
- GPU-based workloads
- Distributed systems
- Cloud execution

### 10.7 Pattern 7: Custom Backend

**Use Case**: Integration with custom execution environment (e.g., cloud services).

**Implementation**:

```python
from deepagents.backends.protocol import SandboxBackendProtocol
import boto3
import json

class LambdaBackend(SandboxBackendProtocol):
    """Execute operations via AWS Lambda."""

    def __init__(self, function_name, s3_bucket):
        self.lambda_client = boto3.client('lambda')
        self.s3_client = boto3.client('s3')
        self.function_name = function_name
        self.bucket = s3_bucket

    def execute(self, command: str, workdir: str = None) -> str:
        """Execute command via Lambda function."""
        response = self.lambda_client.invoke(
            FunctionName=self.function_name,
            InvocationType='RequestResponse',
            Payload=json.dumps({
                'command': command,
                'workdir': workdir
            })
        )
        result = json.loads(response['Payload'].read())
        return result['output']

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

    def ls(self, path: str) -> list[str]:
        """List S3 objects."""
        response = self.s3_client.list_objects_v2(
            Bucket=self.bucket,
            Prefix=path.lstrip('/')
        )
        return [obj['Key'] for obj in response.get('Contents', [])]

# Usage
from langchain.agents import create_agent
from langchain_anthropic import ChatAnthropic
from deepagents.middleware.filesystem import FilesystemMiddleware

model = ChatAnthropic(model="claude-sonnet-4-5")

backend = LambdaBackend(
    function_name="agent-executor",
    s3_bucket="agent-workspace"
)

backend_factory = lambda rt: backend

middleware = [
    FilesystemMiddleware(backend=backend_factory)
]

agent = create_agent(
    model=model,
    system_prompt="You are a cloud-native assistant.",
    tools=[],
    middleware=middleware,
)
```

**When to Use**:
- Cloud-native deployments
- Serverless architectures
- Custom execution environments
- Integration with existing infrastructure

---


---

**Navigation**: [⬅️ Part 4: Skills & Decision](part4-skills-decision.md) | [Index](INDEX.md) | [Part 6: Comparison & Patterns ➡️](part6-comparison-patterns.md)
