# Skill Agent POC

A proof-of-concept demonstrating how to build a skill-based agent using the **Deep Agents SDK**:

- **deepagents** - Official SDK for skill-based agents
- **DockerBackend** - Sandboxed execution environment in Docker containers
- **CompositeBackend** - Route-based path resolution for multiple directories
- **FilesystemMiddleware** - File tools (ls, read_file, write_file, etc.)
- **SkillsMiddleware** - Skill discovery and loading
- **Web Search** - DuckDuckGo search integration for real-time information
- **Multi-turn Conversation** - Persistent conversation memory via LangGraph checkpointer
- **Azure OpenAI** - LLM backend

## Features

### Core Capabilities

| Feature | Description |
|---------|-------------|
| **Sandboxed Execution** | All commands run in isolated Docker containers |
| **Skill System** | Auto-discovery of skills from `/skills/` directory |
| **File Operations** | Read, write, edit files in `/workspace/` |
| **Web Search** | Real-time search via DuckDuckGo |
| **Multi-turn Memory** | Conversation history persisted across turns |
| **PDF Generation** | Markdown to PDF conversion (WeasyPrint) |

### Available Skills

| Skill | Description |
|-------|-------------|
| `file-hash` | Calculate MD5/SHA256/SHA512 hashes of files |
| `content-research-writer` | Research topics and produce written content with PDF output |

## Architecture

### SDK Component Relationships

```
┌────────────────────────────────────────────────────────────┐
│                    create_skill_agent()                    │
│                                                            │
│  model ──────────────────────┐                            │
│  tools (DuckDuckGoSearch) ───┼──→ CompiledStateGraph      │
│  middleware ─────────────────┤    (LangGraph)             │
│  checkpointer ───────────────┤                            │
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
│  - execute            │               │                       │
└───────────────────────┘               └───────────────────────┘
```

### Multi-turn Conversation Flow

```
┌─────────────────────────────────────────────────────────────┐
│                    InMemorySaver (Checkpointer)            │
│                                                             │
│  thread_id: "abc-123"                                       │
│  ┌─────────────────────────────────────────────────────────┐
│  │ Turn 1: User: "我叫小明"                                  │
│  │         Agent: "你好小明！有什麼可以幫你的？"              │
│  ├─────────────────────────────────────────────────────────┤
│  │ Turn 2: User: "我叫什麼名字？"                            │
│  │         Agent: "你叫小明。" (記得之前的對話)              │
│  └─────────────────────────────────────────────────────────┘
└─────────────────────────────────────────────────────────────┘
```

### Skills Directory Structure

```
skills/
├── file-hash/
│   ├── SKILL.md              <- Skill metadata & instructions
│   └── scripts/
│       └── hash_file.py      <- Hash calculation script
│
└── content-research-writer/
    ├── SKILL.md              <- Research & writing workflow
    └── scripts/
        └── generate_pdf.py   <- Markdown to PDF conversion
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

This creates a sandboxed environment with:
- Python 3.11
- Data science packages (pandas, numpy, matplotlib, etc.)
- PDF generation (markdown2, weasyprint)

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

#### File Operations
```
You: 列出 workspace 目錄的檔案
Agent: [Using ls("/workspace/")]
       Files in workspace:
       - sample.csv
       - test_document.txt
```

#### Web Search
```
You: 搜尋 LangChain 最新版本的功能
Agent: [Using duckduckgo_search]
       Based on my search, LangChain v0.3 introduces...
```

#### Multi-turn Conversation
```
You: 我叫小明
Agent: 你好小明！很高興認識你。有什麼我可以幫忙的嗎？

You: 我叫什麼名字？
Agent: 你叫小明。
```

#### Content Research & PDF Generation
```
You: 寫一篇關於 AI Agent 架構的技術文章，產出 PDF
Agent: I'll help you create a technical article about AI Agent architecture.

       [Step 1: Creating outline...]
       [Step 2: Researching with web search...]
       [Step 3: Writing content...]
       [Step 4: Generating PDF...]

       Done! The article has been saved to:
       - /workspace/content.md (Markdown)
       - /workspace/content.pdf (PDF)
```

#### File Hash Calculation
```
You: 計算 test_document.txt 的 SHA256 hash
Agent: [Executing in Docker: python /skills/file-hash/scripts/hash_file.py ...]

       File: test_document.txt
       Size: 585 B
       SHA256: a3b2c1d4e5f6...
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
│   └── *.md, *.pdf              # Generated content files
├── traces/                      # Session trace logs
└── skills/
    ├── file-hash/
    │   ├── SKILL.md
    │   └── scripts/
    │       └── hash_file.py
    └── content-research-writer/
        ├── SKILL.md
        └── scripts/
            └── generate_pdf.py
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
   python /skills/my-skill/scripts/my_script.py <args>
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

## Configuration

### Conversation Memory

The agent uses `InMemorySaver` for conversation persistence:

```python
from langgraph.checkpoint.memory import InMemorySaver

checkpointer = InMemorySaver()
agent = create_skill_agent(
    ...,
    checkpointer=checkpointer,
)

# Each session gets a unique thread_id
config = {"configurable": {"thread_id": "session_123"}}
result = agent.invoke(inputs, config=config)
```

For production, consider using persistent checkpointers:
- `SqliteSaver` - SQLite-based persistence
- `PostgresSaver` - PostgreSQL-based persistence

### Web Search

The agent includes DuckDuckGo search (no API key required):

```python
from langchain_community.tools import DuckDuckGoSearchResults

search_tool = DuckDuckGoSearchResults(max_results=5)
```

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
| `langchain-community` | DuckDuckGo search tool |
| `ddgs` | DuckDuckGo search backend |
| `python-dotenv` | Environment variable loading |
| `pypdf` (optional) | PDF text extraction |
| `markdown2` (optional) | Markdown to HTML conversion |
| `weasyprint` (optional) | HTML to PDF generation |

Install optional dependencies:
```bash
uv sync --extra pdf    # For PDF processing & generation
uv sync --extra all    # All optional deps
```

## Troubleshooting

### DuckDuckGo Search Error

If you see `Could not import ddgs python package`:
```bash
uv sync  # Ensure ddgs is installed
```

### Docker Container Not Starting

```bash
# Check Docker is running
docker ps

# Rebuild image if needed
docker build -t skill-agent:latest .

# Check container logs
docker logs skill-agent-container
```

### PDF Generation Fails

Ensure WeasyPrint dependencies are installed in the Docker image:
```bash
docker build -t skill-agent:latest .  # Rebuild image
```

## License

MIT
