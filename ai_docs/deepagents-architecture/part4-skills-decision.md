# DeepAgents CLI vs SDK Architecture - Part 4: Skills & Decision Framework

> **Navigation**: [⬅️ Part 3: Middleware & Execution](part3-middleware-execution.md) | [Index](INDEX.md) | [Part 5: Implementation ➡️](part5-implementation.md)

**Sections**: 8-9 | Skills System, Decision Framework

---

## 8. Skills System

This section covers the skills system in detail, including discovery, progressive disclosure, and implementation in CLI vs SDK.

### 8.1 What Are Skills?

Skills are a standardized way to extend agent capabilities with:
1. **Structured documentation** (SKILL.md with YAML frontmatter)
2. **Executable code** (Python scripts, bash scripts, etc.)
3. **Reference materials** (examples, documentation)

**Key Benefits**:
- **Self-documenting**: Easy to understand what a skill does
- **Portable**: Skills are just files
- **Discoverable**: Automatic discovery by agents
- **Extensible**: Can include any type of code or reference material

### 8.2 SKILL.md Specification

#### Minimal SKILL.md

```yaml
---
name: my-skill
description: Brief description of what this skill does and when to use it.
---

# Skill Instructions

Detailed instructions for using this skill.

## Usage

```bash
python /skills/my-skill/scripts/script.py <args>
```

## Examples

...
```

#### Full SKILL.md with Metadata

```yaml
---
name: file-hash
description: Calculate cryptographic hashes (MD5, SHA256, SHA512) of files.
license: MIT
metadata:
  author: example-org
  version: "1.0.0"
  requires: python3
compatibility: Requires Python 3.6+
allowed-tools: execute, read_file
---

# File Hash Calculation

This skill computes cryptographic hashes of files using Python's hashlib library.

## Usage

```bash
python /skills/file-hash/scripts/hash_file.py <file_path> <algorithm>
```

## Algorithms

- md5 - MD5 hash (128-bit)
- sha256 - SHA-256 hash (256-bit)
- sha512 - SHA-512 hash (512-bit)

## Examples

### Calculate SHA-256 hash

```bash
python /skills/file-hash/scripts/hash_file.py /workspace/document.pdf sha256
```

Output:
```
a3c5d2e8f1b4c7a9d2e5f8b1c4a7d0e3f6b9c2e5f8b1c4a7d0e3f6b9c2e5f8b1
```

## Implementation Notes

This skill MUST use the Python script because:
1. AI models cannot compute cryptographic hashes directly
2. Hashing requires binary file processing
3. hashlib provides secure, standardized implementations
```

#### Field Reference

| Field | Required | Description |
|-------|----------|-------------|
| `name` | Yes | Skill identifier (lowercase, hyphens only) |
| `description` | Yes | What the skill does and when to use it (max 1024 chars) |
| `license` | No | License identifier or file reference |
| `compatibility` | No | Environment requirements |
| `metadata` | No | Arbitrary key-value pairs |
| `allowed-tools` | No | Pre-approved tools (experimental) |

### 8.3 Progressive Disclosure

Skills use progressive disclosure to manage context efficiently:

```
Level 1: Discovery (Startup)
    Load: name + description only
    Tokens: ~100 total
    Purpose: Know what skills exist
    ↓
Level 2: Activation (On-Demand)
    Load: Full SKILL.md content
    Tokens: <5000 per skill (recommended)
    Purpose: Understand how to use skill
    ↓
Level 3: Execution (As Needed)
    Load: Scripts, references, examples
    Tokens: Variable
    Purpose: Execute skill functionality
```

#### Level 1: Discovery Example

```
<available_skills>
- file-hash: Calculate cryptographic hashes (MD5, SHA256, SHA512) of files.
- data-analysis: Analyze datasets and generate statistical reports.
- web-scraper: Extract structured data from web pages.
</available_skills>
```

**Token Usage**: ~30 tokens per skill × 3 skills = ~90 tokens

#### Level 2: Activation Example

User: "Calculate the SHA-256 hash of document.pdf"

Agent sees "file-hash" skill is relevant, reads full documentation:

```python
read_file("/skills/file-hash/SKILL.md")
```

Returns full SKILL.md content (~2000 tokens)

Agent now understands:
- How to use the skill
- What commands to run
- What arguments to provide

#### Level 3: Execution Example

Agent executes skill:

```python
execute(
    command="python /skills/file-hash/scripts/hash_file.py /workspace/document.pdf sha256"
)
```

Output: `a3c5d2e8f1b4c7a9d2e5f8b1c4a7d0e3f6b9c2e5f8b1c4a7d0e3f6b9c2e5f8b1`

### 8.4 Skills Discovery in CLI

CLI tools (like Claude Code) don't have built-in skills support. Skills must be:

1. **Manually documented** in system prompt
2. **Explicitly referenced** by user
3. **Executed via bash tool**

#### Manual Skills Integration

```python
system_prompt = """You have access to the following skills:

## file-hash
Calculate cryptographic hashes of files.
Usage: python /path/to/skills/file-hash/scripts/hash_file.py <file> <algorithm>

## data-analysis
Analyze datasets and generate reports.
Usage: python /path/to/skills/data-analysis/scripts/analyze.py <dataset>
"""

# Agent uses bash tool to execute skills
bash("python /path/to/skills/file-hash/scripts/hash_file.py document.pdf sha256")
```

**Limitations**:
- No automatic discovery
- No progressive disclosure
- Manual maintenance of skill documentation
- Full skill documentation in prompt (high token cost)

### 8.5 Skills Discovery in SDK

SDK uses SkillsMiddleware for automatic discovery:

```python
middleware = [
    SkillsMiddleware(
        backend=backend_factory,
        sources=["/skills/", "/custom-skills/"]
    ),
    FilesystemMiddleware(backend=backend_factory),
    # Other middleware...
]
```

#### Discovery Flow

```
Agent Startup
    ↓
SkillsMiddleware.before_model()
    ↓
For each source in sources:
    backend.ls(source)  # List directories
    ↓
    For each directory:
        Try reading: {source}/{dir}/SKILL.md
        ↓
        Parse YAML frontmatter
        ↓
        Extract: name, description
        ↓
        Store in skills registry
    ↓
Inject into system prompt:
<available_skills>
{list of name: description}
</available_skills>
    ↓
Agent receives minimal skill context (Level 1)
```

#### On-Demand Loading

```
User: "Calculate SHA-256 of document.pdf"
    ↓
Agent sees "hash" and "SHA-256" → relevant to "file-hash" skill
    ↓
Agent: read_file("/skills/file-hash/SKILL.md")
    ↓
FilesystemMiddleware routes to backend
    ↓
Backend returns full SKILL.md content (Level 2)
    ↓
Agent understands how to use skill
    ↓
Agent: execute("python /skills/file-hash/scripts/hash_file.py ...")
    ↓
FilesystemMiddleware routes to DockerBackend (Level 3)
    ↓
Result returned to agent
```

### 8.6 Skills Backend Configuration

Skills require careful backend configuration to work correctly:

```python
# Incorrect: Skills can't be read
backend = DockerBackend(...)  # No access to host skills directory

# Correct: Skills accessible via CompositeBackend route
backend = CompositeBackend(
    default=DockerBackend(
        volumes={
            "/host/skills": "/skills",  # Mount for execution
        }
    ),
    routes={
        "/skills/": FilesystemBackend(  # Fast host reads
            root_dir="/host/skills",
            virtual_mode=True
        ),
    }
)
```

**Why This Works**:
1. **Discovery**: SkillsMiddleware reads SKILL.md via FilesystemBackend route (fast)
2. **Documentation**: Agent reads full SKILL.md via FilesystemBackend route (fast)
3. **Execution**: Agent executes scripts via DockerBackend with volume mount (sandboxed)

### 8.7 Skill Execution Patterns

#### Pattern 1: Python Script

```yaml
---
name: data-processor
description: Process and transform data files.
---

## Usage

```bash
python /skills/data-processor/scripts/process.py <input> <output> <format>
```
```

**Agent Execution**:
```python
execute("python /skills/data-processor/scripts/process.py /workspace/data.csv /workspace/result.json json")
```

#### Pattern 2: Bash Script

```yaml
---
name: system-info
description: Gather system information.
---

## Usage

```bash
bash /skills/system-info/scripts/info.sh
```
```

**Agent Execution**:
```python
execute("bash /skills/system-info/scripts/info.sh")
```

#### Pattern 3: Multi-Step Workflow

```yaml
---
name: ml-training
description: Train machine learning models.
---

## Usage

### Step 1: Prepare data

```bash
python /skills/ml-training/scripts/prepare.py <dataset>
```

### Step 2: Train model

```bash
python /skills/ml-training/scripts/train.py <config>
```

### Step 3: Evaluate

```bash
python /skills/ml-training/scripts/evaluate.py <model> <test_data>
```
```

**Agent Execution**:
```python
# Step 1
execute("python /skills/ml-training/scripts/prepare.py /workspace/data.csv")

# Step 2
execute("python /skills/ml-training/scripts/train.py /workspace/config.yaml")

# Step 3
execute("python /skills/ml-training/scripts/evaluate.py /workspace/model.pkl /workspace/test.csv")
```

### 8.8 Skills Directory Structure Best Practices

#### Recommended Structure

```
skills/
├── skill-name/
│   ├── SKILL.md              # Required: Skill documentation
│   ├── scripts/              # Recommended: Executable scripts
│   │   ├── main.py          # Main entry point
│   │   └── utils.py         # Helper modules
│   ├── references/           # Optional: Reference documentation
│   │   ├── examples.md      # Usage examples
│   │   └── api-docs.md      # API documentation
│   ├── assets/               # Optional: Static assets
│   │   └── template.json    # Templates, configs
│   └── tests/                # Optional: Tests
│       └── test_main.py     # Unit tests
```

#### Multiple Skills

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

### 8.9 Skills vs Tools

**Skills**:
- File-based documentation
- Executable scripts
- Discovered automatically (SDK)
- Progressive disclosure
- Portable across agents

**Tools**:
- Programmatic functions
- Defined in code
- Generated by middleware
- Always available
- Agent-specific

**When to Use Skills**:
- Complex workflows requiring multiple steps
- Domain-specific knowledge that needs documentation
- Functionality that requires executable code
- Reusable capabilities across different agents
- External dependencies (APIs, libraries)

**When to Use Tools**:
- Simple operations (read file, list directory)
- Core agent capabilities (file operations, execution)
- Stateful operations (state management)
- Performance-critical operations

### 8.10 Skills Token Management

Managing token usage with skills:

#### Problem: Too Many Skills

```
<available_skills>
- skill-1: ...
- skill-2: ...
... (100 skills)
- skill-100: ...
</available_skills>
```

**Token Cost**: ~30 tokens/skill × 100 = ~3000 tokens (too expensive!)

#### Solution 1: Selective Sources

```python
# Don't load all skills
SkillsMiddleware(
    sources=[
        "/skills/core/",      # Only core skills
        "/skills/user-selected/",  # User's active skills
    ]
)
```

#### Solution 2: Lazy Loading

```python
# Load skill list, but not descriptions
SkillsMiddleware(
    sources=["/skills/"],
    lazy_load=True  # Only load descriptions when skill is accessed
)
```

#### Solution 3: Skill Categories

```
<available_skills>
Categories:
- data: file-hash, data-analysis, csv-processor (3 skills)
- web: web-scraper, api-client, html-parser (3 skills)
- ml: ml-training, model-eval, feature-engineering (3 skills)

Use read_file() to see details for specific category.
</available_skills>
```

**Token Cost**: ~200 tokens (much better!)

---

## 9. Decision Framework

This section provides a systematic framework for choosing between CLI and SDK approaches.

### 9.1 Decision Tree

```
START: Need to build an AI agent
    ↓
Question 1: Do you need sandboxed execution?
    ├─ YES → Use SDK with DockerBackend or RemoteBackend
    │         Continue to Question 3
    └─ NO → Continue to Question 2

Question 2: Do you need custom middleware or backends?
    ├─ YES → Use SDK
    │         Continue to Question 3
    └─ NO → Continue to Question 2a

Question 2a: Is this for rapid prototyping or development?
    ├─ YES → Use CLI (Claude Code, etc.)
    │         ✓ Fast iteration
    │         ✓ Simple setup
    │         ✓ Good for learning
    └─ NO → Use SDK with StateBackend only
              ✓ Portable code
              ✓ Programmatic control

Question 3 (SDK path): What execution environment?
    ├─ Local Docker → DockerBackend
    ├─ Remote Server → RemoteBackend
    ├─ Cloud/Lambda → Custom Backend
    └─ No Execution → StateBackend only

Question 4: Do you need skills?
    ├─ YES → Add SkillsMiddleware + setup skills directory
    └─ NO → Skip skills

Question 5: Do you need task delegation?
    ├─ YES → Add SubAgentMiddleware
    └─ NO → Skip sub-agents

RESULT: Your architecture
```

### 9.2 Use Case Decision Matrix

| Use Case | Recommended Approach | Rationale |
|----------|---------------------|-----------|
| Personal automation | CLI | Simple, fast, trusted environment |
| Development/Testing | CLI or SDK (minimal) | Quick iteration, easy debugging |
| Production single-user | SDK (DockerBackend) | Sandboxing, reliability |
| Production multi-user | SDK (DockerBackend) | Isolation, security |
| Distributed computing | SDK (RemoteBackend) | Scale, resource management |
| Learning AI agents | CLI | Minimal complexity, focus on agent behavior |
| Complex workflows | SDK (full stack) | Skills, sub-agents, custom middleware |
| Security-critical | SDK (DockerBackend) | Sandboxing, access control |
| Cloud deployment | SDK (Custom backend) | Integration with cloud services |
| Edge devices | SDK (lightweight) | Resource constraints, portability |

### 9.3 Feature Requirements Checklist

Use this checklist to determine which features you need:

**Execution Environment**:
- [ ] Need sandboxed execution → DockerBackend
- [ ] Need remote execution → RemoteBackend
- [ ] Need cloud integration → Custom Backend
- [ ] Trust agent fully → CLI or SDK with ShellMiddleware

**Functionality**:
- [ ] Need skills system → SkillsMiddleware
- [ ] Need task delegation → SubAgentMiddleware
- [ ] Need custom tools → Custom Middleware
- [ ] Need conversation management → TodoListMiddleware
- [ ] Need context management → SummarizationMiddleware

**Performance**:
- [ ] Need fast file reads → CompositeBackend with FilesystemBackend routes
- [ ] Need low latency → CLI or local DockerBackend
- [ ] Need high throughput → RemoteBackend or distributed setup

**Security**:
- [ ] Untrusted code execution → DockerBackend (required)
- [ ] Multi-tenant → DockerBackend with resource limits
- [ ] Data isolation → Separate backend instances per user
- [ ] Audit logging → Custom middleware for logging

### 9.4 Complexity vs Capability

```
High Capability
    ↑
    │                    ┌─────────────────────────┐
    │                    │ SDK Full Stack          │
    │                    │ (Docker + Skills +      │
    │                    │  SubAgents + Custom)    │
    │                    └─────────────────────────┘
    │            ┌─────────────────────────┐
    │            │ SDK with DockerBackend  │
    │            │ (Sandboxed execution)   │
    │            └─────────────────────────┘
    │    ┌─────────────────────────┐
    │    │ SDK Minimal             │
    │    │ (StateBackend only)     │
    │    └─────────────────────────┘
    │┌─────────────────────────┐
    ││ CLI (Claude Code)       │
    ││ (Direct execution)      │
    │└─────────────────────────┘
    └────────────────────────────────────→
                           High Complexity
```

### 9.5 Migration Path

```
Phase 1: Prototype with CLI
    ↓
    Quick learning, fast iteration
    ↓
Phase 2: Move to SDK (minimal)
    ↓
    Structured code, programmatic control
    ↓
Phase 3: Add Sandboxing
    ↓
    DockerBackend for isolation
    ↓
Phase 4: Add Skills
    ↓
    SkillsMiddleware + skills directory
    ↓
Phase 5: Full Production
    ↓
    SubAgents, custom middleware, monitoring
```

### 9.6 Cost Considerations

**Development Cost**:
- **CLI**: Low (hours to get started)
- **SDK Minimal**: Medium (1-2 days setup)
- **SDK Full**: High (1-2 weeks for complete setup)

**Operational Cost**:
- **CLI**: User's machine resources
- **SDK Docker**: Container resources (~100MB RAM + CPU)
- **SDK Remote**: Remote server costs (variable)

**Maintenance Cost**:
- **CLI**: Low (few components to maintain)
- **SDK**: Medium to High (backends, middleware, skills)

### 9.7 Decision Examples

#### Example 1: Personal Task Automation

**Requirements**:
- Automate personal tasks (email, file organization)
- Single user (me)
- Trusted environment (my laptop)
- Fast iteration

**Decision**: CLI (Claude Code)

**Rationale**:
- No sandboxing needed (trusted)
- Simple setup
- Fast iteration
- Low complexity

#### Example 2: Customer Service Agent

**Requirements**:
- Handle customer queries
- Execute code (data lookups, calculations)
- Multiple customers (security required)
- Production deployment

**Decision**: SDK with DockerBackend

**Rationale**:
- Sandboxing required (multi-tenant)
- Isolation between customers
- Production reliability
- Structured deployment

#### Example 3: Data Analysis Platform

**Requirements**:
- Analyze datasets
- Train ML models
- Specialized data analysis skills
- Task delegation for complex workflows
- High-performance computing

**Decision**: SDK Full Stack (Docker + Skills + SubAgents + RemoteBackend)

**Rationale**:
- Skills for domain-specific operations
- SubAgents for complex workflows
- RemoteBackend for GPU servers
- Full capabilities needed

#### Example 4: Learning AI Agents

**Requirements**:
- Understand how AI agents work
- Experiment with different prompts
- No production requirements
- Focus on agent behavior, not infrastructure

**Decision**: CLI (Claude Code)

**Rationale**:
- Minimal complexity
- Focus on agent learning
- Fast experimentation
- No infrastructure overhead

---


---

**Navigation**: [⬅️ Part 3: Middleware & Execution](part3-middleware-execution.md) | [Index](INDEX.md) | [Part 5: Implementation ➡️](part5-implementation.md)
