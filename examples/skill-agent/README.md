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
      │  └─ python skills/file-hash/scripts/hash_file.py
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

You: 讀取 test_document.txt 的內容
Agent: [Using read_file("/workspace/test_document.txt")]
       File Hash Test Document
       =======================
       ...

You: 計算 test_document.txt 的 SHA256 hash
Agent: I'll calculate the hash for you...
       [Executing: python skills/file-hash/scripts/hash_file.py workspace/test_document.txt --algo sha256]

Agent: Here's the SHA256 hash of your file:
       File: test_document.txt
       Size: 585 B
       SHA256: a3b2c1d4e5f6...

       Note: This demonstrates mandatory script execution - the AI cannot compute
       cryptographic hashes directly and must execute the hash script.
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

**Note**: The file-hash skill uses only Python standard library (`hashlib`, `pathlib`, `sys`, `argparse`) and requires no additional dependencies.

Install optional dependencies:
```bash
uv sync --extra pdf    # For PDF processing
uv sync --extra all    # All optional deps
```

## License

MIT
