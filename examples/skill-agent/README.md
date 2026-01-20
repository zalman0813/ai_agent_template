# Skill Agent POC

A proof-of-concept demonstrating how to build a skill-based agent using the **Deep Agents SDK**:

- **deepagents** - Official SDK for skill-based agents
- **CompositeBackend** - Route-based path resolution for multiple directories
- **FilesystemMiddleware** - File tools (ls, read_file, write_file, etc.)
- **SkillsMiddleware** - Skill discovery and loading
- **Azure OpenAI** - LLM backend
- **Bash Tool** - Script execution

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
│  Route-based path resolution:                              │
│  /skills/*    → FilesystemBackend(root_dir="./skills")    │
│  /workspace/* → FilesystemBackend(root_dir="./workspace") │
│  default      → StateBackend (temporary storage)          │
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
| `/skills/data-analysis/SKILL.md` | `/skills/` | `./skills/data-analysis/SKILL.md` |
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
└── data-analysis/
    ├── SKILL.md
    └── scripts/
        └── analyze.py
```

## Execution Flow

```
1. Startup
   └─ create_skill_agent()
      ├─ CompositeBackend with routes:
      │  ├─ /skills/    → FilesystemBackend("./skills")
      │  ├─ /workspace/ → FilesystemBackend("./workspace")
      │  └─ default     → StateBackend
      ├─ FilesystemMiddleware (file tools)
      ├─ SkillsMiddleware(backend, sources=["./skills"])
      └─ create_deep_agent(model, tools, middleware, backend)

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
      │
      ├─ Tool execution (bash_tool)
      │  └─ python skills/data-analysis/scripts/analyze.py
      │
      └─ Return result
```

## Quick Start

### 1. Install Dependencies

```bash
cd examples/skill-agent
uv sync
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env with your Azure OpenAI credentials
```

Required variables:
- `AZURE_OPENAI_API_KEY` - Your API key
- `AZURE_OPENAI_ENDPOINT` - e.g., `https://your-resource.openai.azure.com/`
- `AZURE_OPENAI_DEPLOYMENT_NAME` - e.g., `gpt-4o`

### 3. Run the Agent

```bash
uv run python main.py
```

### 4. Example Interactions

```
You: 列出 workspace 目錄的檔案
Agent: [Using ls("/workspace/")]
       Files in workspace:
       - sample.csv

You: 讀取 sample.csv 的內容
Agent: [Using read_file("/workspace/sample.csv")]
       Here's the content of sample.csv:
       name,age,city,salary
       ...

You: 分析 sample.csv
Agent: I'll analyze the CSV file for you...
       [Using read_file("/workspace/sample.csv") to check the file]
       [Executing: python skills/data-analysis/scripts/analyze.py workspace/sample.csv]

Agent: Here's the analysis of your CSV file:
       - 10 records with columns: name, age, city, salary
       - Average salary: 85,100
       ...
```

## Project Structure

```
examples/skill-agent/
├── README.md                    # This file
├── pyproject.toml               # UV package config
├── .env.example                 # Environment template
├── main.py                      # CLI entry point
├── agent.py                     # Agent creation with SDK
├── tools/
│   ├── __init__.py
│   └── bash_tool.py             # Bash execution tool
├── workspace/                   # User files directory
│   └── sample.csv               # Sample data for testing
└── skills/
    ├── pdf-processing/
    │   ├── SKILL.md             # Skill definition
    │   └── scripts/
    │       └── extract_text.py  # PDF extraction script
    └── data-analysis/
        ├── SKILL.md
        └── scripts/
            └── analyze.py       # Data analysis script
```

## Workspace

Place your data files in the `workspace/` directory. The agent is configured to look for files there when you reference them without a full path.

```bash
# Put your CSV files here
cp mydata.csv workspace/

# Then ask the agent
You: 分析 mydata.csv
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

## Security Notes

The `bash_tool` has safety restrictions:

- **Allowed commands**: `python`, `python3`, `cat`, `head`, `tail`, `ls`, `pwd`, `echo`, `grep`, `wc`
- **Blocked patterns**: Destructive commands like `rm -rf /`
- **Timeout**: 30 seconds default

To modify these restrictions, edit `tools/bash_tool.py`.

## Dependencies

| Package | Purpose |
|---------|---------|
| `deepagents` | Deep Agents SDK (CompositeBackend, FilesystemMiddleware, SkillsMiddleware) |
| `langchain-openai` | Azure OpenAI integration |
| `python-dotenv` | Environment variable loading |
| `pypdf` (optional) | PDF text extraction |
| `pandas` (optional) | Data analysis |

Install optional dependencies:
```bash
uv sync --extra pdf    # For PDF processing
uv sync --extra data   # For data analysis
uv sync --extra all    # All optional deps
```

## License

MIT
