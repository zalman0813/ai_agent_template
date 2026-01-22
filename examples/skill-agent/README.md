# Skill Agent POC

A proof-of-concept demonstrating how to build a skill-based agent using the **Deep Agents SDK**:

- **deepagents** - Official SDK for skill-based agents
- **DockerBackend** - Sandboxed execution environment in Docker containers
- **CompositeBackend** - Route-based path resolution for multiple directories
- **FilesystemMiddleware** - File tools (ls, read_file, write_file, etc.)
- **SkillsMiddleware** - Skill discovery and loading
- **Azure OpenAI** - LLM backend

## ⚠️ Breaking Change: Docker-Based Execution

**Version 2.0** introduces Docker-based sandboxed execution:
- **New requirement**: Docker must be installed and running
- **Migration**: See [Docker Setup Guide](backends/DOCKER_SETUP.md) for setup instructions
- **Benefits**: Isolated execution, reproducible environment, enhanced security
- **Removed**: `ExecutableCompositeBackend` and monkey patches (cleaner codebase)

## Architecture

### SDK Component Relationships

```
┌────────────────────────────────────────────────────────────┐
│                    create_deep_agent()                     │
│                                                            │
│  model ──────────────────────┐                            │
│  tools ──────────────────────┼──→ CompiledStateGraph      │
│  middleware ─────────────────┤    (LangGraph)             │
│  backend ────────────────────┤                            │
│  system_prompt ──────────────┘                            │
└────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌────────────────────────────────────────────────────────────┐
│                    CompositeBackend                        │
│                                                            │
│  Route-based path resolution + sandboxed execution:        │
│  /skills/*    → FilesystemBackend("./skills") [host]      │
│  /workspace/* → FilesystemBackend("./workspace") [host]   │
│  default      → DockerBackend (sandboxed execution)       │
│                                                            │
│  DockerBackend: skill-agent:latest container               │
│  Volumes: /skills, /workspace mounted from host            │
└────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┴─────────────────────┐
        ▼                                           ▼
┌───────────────────────┐               ┌───────────────────────┐
│  FilesystemMiddleware │               │   SkillsMiddleware    │
│                       │               │                       │
│  Provides file tools: │               │  Discovers SKILL.md   │
│  - ls                 │               │  Injects into prompt  │
│  - read_file          │               │                       │
│  - write_file         │               │  Uses: FilesystemBackend
│  - edit_file          │               │  to load skill content│
│  - glob               │               │                       │
│  - grep               │               │                       │
└───────────────────────┘               └───────────────────────┘
```

### Path Resolution

| Agent Request Path | Route Prefix | Actual File Path |
|---|---|---|
| `/skills/file-hash/SKILL.md` | `/skills/` | `./skills/file-hash/SKILL.md` |
| `/workspace/sample.csv` | `/workspace/` | `./workspace/sample.csv` |
| `/temp.txt` | (no match) | StateBackend temporary storage |

### Skills Directory Structure

```
skills/
├── pdf-processing/
│   ├── SKILL.md              <- Skill metadata & instructions
│   └── scripts/
│       └── extract_text.py   <- Executable script
│
└── file-hash/
    ├── SKILL.md
    └── scripts/
        └── hash_file.py      <- Hash calculation script
```

## Execution Flow

```
1. Startup
   └─ create_skill_agent()
      ├─ DockerBackend (auto-creates/starts container)
      │  ├─ Container: skill-agent-container
      │  ├─ Image: skill-agent:latest
      │  └─ Volumes: /skills, /workspace from host
      ├─ CompositeBackend with routes:
      │  ├─ /skills/    → FilesystemBackend("./skills") [host reads]
      │  ├─ /workspace/ → FilesystemBackend("./workspace") [host reads]
      │  └─ default     → DockerBackend [sandboxed execution]
      ├─ FilesystemMiddleware (file tools)
      ├─ SkillsMiddleware(backend, sources=["/skills/"])
      └─ create_agent(model, tools=[], middleware)

2. Conversation
   └─ agent.invoke({"messages": [...]})
      │
      ├─ SkillsMiddleware.before_agent()
      │  └─ Scan skills/ for SKILL.md
      │  └─ Parse YAML frontmatter (name, description)
      │
      ├─ SkillsMiddleware.wrap_model_call()
      │  └─ Inject <available_skills> into system prompt
      │
      ├─ Model decides which skill to use
      │
      ├─ File tools via FilesystemMiddleware
      │  └─ ls("/workspace/"), read_file("/workspace/sample.csv")
      │     [Routes to FilesystemBackend on host - fast reads]
      │
      ├─ Tool execution (execute via FilesystemMiddleware)
      │  └─ execute("python /skills/file-hash/scripts/hash_file.py /workspace/test_document.txt")
      │     [Delegates to DockerBackend - sandboxed in container]
      │     [Container accesses files via volumes]
      │
      └─ Return result
```

## Quick Start

### Prerequisites

- **Docker**: Required for sandboxed execution
  - [Install Docker Desktop](https://www.docker.com/products/docker-desktop) (macOS/Windows)
  - [Install Docker Engine](https://docs.docker.com/engine/install/) (Linux)
  - Verify: `docker --version`

- **Python 3.11+**: Required for running the agent
- **UV**: Python package manager (recommended)

### 1. Install Dependencies

```bash
cd examples/skill-agent
uv sync
```

### 2. Build Docker Image

```bash
# Build custom Docker image for skill execution
docker build -t skill-agent:latest .
```

This creates a sandboxed environment with Python 3.11 and common dependencies.

**Note**: The agent will auto-create and start the container on first run.

### 3. Configure Environment

```bash
cp .env.example .env
# Edit .env with your Azure OpenAI credentials
```

Required variables:
- `AZURE_OPENAI_API_KEY` - Your API key
- `AZURE_OPENAI_ENDPOINT` - e.g., `https://your-resource.openai.azure.com/`
- `AZURE_OPENAI_DEPLOYMENT_NAME` - e.g., `gpt-4o`

### 4. Run the Agent

```bash
uv run python main.py
```

**First run**: The agent will automatically create and start the Docker container (takes ~2 seconds).
**Subsequent runs**: The agent reuses the existing container (instant startup).

### 5. Example Interactions

```
You: 列出 workspace 目錄的檔案
Agent: [Using ls("/workspace/")]
       Files in workspace:
       - sample.csv

You: 讀取 test_document.txt 的內容
Agent: [Using read_file("/workspace/test_document.txt")]
       File Hash Test Document
       =======================
       ...

You: 計算 test_document.txt 的 SHA256 hash
Agent: I'll calculate the hash for you...
       [Executing in Docker container: python /skills/file-hash/scripts/hash_file.py /workspace/test_document.txt --algo sha256]

Agent: Here's the SHA256 hash of your file:
       File: test_document.txt
       Size: 585 B
       SHA256: a3b2c1d4e5f6...

       Note: This demonstrates mandatory script execution in a sandboxed Docker container.
       The AI cannot compute cryptographic hashes directly and must execute the hash script.
```

## Project Structure

```
examples/skill-agent/
├── README.md                    # This file
├── pyproject.toml               # UV package config
├── Dockerfile                   # Docker image for sandboxed execution
├── .env.example                 # Environment template
├── main.py                      # CLI entry point
├── agent.py                     # Agent creation with SDK
├── backends/                    # Backend implementations
│   ├── __init__.py
│   ├── docker_backend.py        # DockerBackend for sandboxed execution
│   └── DOCKER_SETUP.md          # Docker setup guide
├── workspace/                   # User files directory
│   ├── sample.csv               # Sample data file
│   ├── test_document.txt        # Test text file
│   ├── test_image.png           # Test binary file
│   └── test_large.bin           # Large test file
└── skills/
    ├── pdf-processing/
    │   ├── SKILL.md             # Skill definition
    │   └── scripts/
    │       └── extract_text.py  # PDF extraction script
    └── file-hash/
        ├── SKILL.md
        └── scripts/
            └── hash_file.py     # Hash calculation script
```

## Workspace

Place your data files in the `workspace/` directory. The agent is configured to look for files there when you reference them without a full path.

The workspace includes test files:
- `test_document.txt` - Small text file for testing
- `test_image.png` - Binary image file
- `test_large.bin` - Large binary file (100KB)
- `sample.csv` - Sample CSV data

```bash
# Put your files here
cp myfile.txt workspace/

# Then ask the agent
You: 計算 myfile.txt 的 MD5 hash
```

## Adding New Skills

1. Create a new directory under `skills/`:
   ```bash
   mkdir -p skills/my-skill/scripts
   ```

2. Create `SKILL.md` with YAML frontmatter:
   ```markdown
   ---
   name: my-skill
   description: Brief description for agent to understand when to use this skill.
   ---

   # My Skill

   ## Usage
   ```bash
   python scripts/my_script.py <args>
   ```
   ```

3. Add your script(s) to `scripts/`:
   ```python
   # skills/my-skill/scripts/my_script.py
   def main():
       # Your skill logic
       pass
   ```

4. Restart the agent - the new skill will be auto-discovered.

## Why File-Hash Skill Demonstrates Mandatory Script Execution

The **file-hash** skill is specifically designed to demonstrate a scenario where **script execution is mandatory** - the AI cannot bypass it by reading files directly.

### The Problem with Data Analysis Skills

Previously, the example used a `data-analysis` skill that could analyze CSV files. However:
- AI can read CSV files using the `read_file` tool
- AI can parse CSV structure and perform statistical calculations in context
- AI can bypass the analysis script entirely by processing data directly
- This makes it unclear when script execution is truly needed

### Why File Hashing Requires Script Execution

Cryptographic hash calculation is fundamentally different because the AI **cannot**:
- ❌ Compute MD5, SHA256, or SHA512 hashes (requires cryptographic algorithms)
- ❌ Process binary files byte-by-byte (images, executables, archives)
- ❌ Perform byte-level cryptographic operations
- ❌ Implement hash algorithms in natural language

**Result**: The AI **must** execute the hash script - no bypass is possible.

### Practical Use Cases

The file-hash skill demonstrates real-world scenarios where script execution is necessary:
- **File Integrity Verification**: Verify downloaded files match expected checksums
- **Duplicate Detection**: Find duplicate files across directories by comparing hashes
- **Change Detection**: Detect if files have been modified
- **Security Auditing**: Calculate hashes for security compliance

This makes it an ideal demonstration of the skill system working as designed.

## Security Notes

### Docker Sandboxing

All skill executions run in an isolated Docker container:

- **Isolated environment**: Code runs in a separate container, not on the host
- **Resource limits**: Docker can limit CPU, memory, and network access
- **Volume-based access**: Only `/skills` and `/workspace` are accessible
- **Reproducible**: Consistent environment defined by `Dockerfile`

### Execution Safety

- **Timeout**: Commands time out after 60 seconds (configurable)
- **Container lifecycle**: Auto-created and managed by DockerBackend
- **Volume mounts**: Only specified directories are accessible in container

For advanced security configuration (resource limits, read-only volumes, network isolation), see [Docker Setup Guide](backends/DOCKER_SETUP.md).

## Dependencies

| Package | Purpose |
|---------|---------|
| `deepagents` | Deep Agents SDK (CompositeBackend, FilesystemMiddleware, SkillsMiddleware) |
| `langchain-openai` | Azure OpenAI integration |
| `python-dotenv` | Environment variable loading |
| `pypdf` (optional) | PDF text extraction |

**Note**: The file-hash skill uses only Python standard library (`hashlib`, `pathlib`, `sys`, `argparse`) and requires no additional dependencies.

Install optional dependencies:
```bash
uv sync --extra pdf    # For PDF processing
uv sync --extra all    # All optional deps
```

## License

MIT
