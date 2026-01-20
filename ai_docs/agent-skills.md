# Agent Skills Open Standard

> Official documentation for the Agent Skills open standard - a lightweight format for extending AI agent capabilities.

**Sources:**
- https://agentskills.io/
- https://github.com/agentskills/agentskills
- https://github.com/anthropics/skills
- https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills

---

## What are Agent Skills?

Agent Skills are a lightweight, open format for extending AI agent capabilities with specialized knowledge and workflows.

At its core, a skill is a folder containing a `SKILL.md` file. This file includes metadata (`name` and `description`, at minimum) and instructions that tell an agent how to perform a specific task. Skills can also bundle scripts, templates, and reference materials.

```
my-skill/
├── SKILL.md          # Required: instructions + metadata
├── scripts/          # Optional: executable code
├── references/       # Optional: documentation
└── assets/           # Optional: templates, resources
```

### Key Advantages

- **Self-documenting**: A skill author or user can read a `SKILL.md` and understand what it does, making skills easy to audit and improve.
- **Extensible**: Skills can range in complexity from just text instructions to executable code, assets, and templates.
- **Portable**: Skills are just files, so they're easy to edit, version, and share.

---

## How Skills Work

Skills use **progressive disclosure** to manage context efficiently:

1. **Discovery**: At startup, agents load only the name and description of each available skill, just enough to know when it might be relevant.
2. **Activation**: When a task matches a skill's description, the agent reads the full `SKILL.md` instructions into context.
3. **Execution**: The agent follows the instructions, optionally loading referenced files or executing bundled code as needed.

This approach keeps agents fast while giving them access to more context on demand.

### Progressive Disclosure Levels

| Level | Content | Token Usage |
|-------|---------|-------------|
| 1. Metadata | `name` and `description` fields | ~100 tokens |
| 2. Instructions | Full `SKILL.md` body | < 5000 tokens recommended |
| 3. Resources | Files in `scripts/`, `references/`, `assets/` | As needed |

---

## SKILL.md Specification

### Directory Structure

A skill is a directory containing at minimum a `SKILL.md` file:

```
skill-name/
└── SKILL.md          # Required
```

### Frontmatter (Required)

```yaml
---
name: skill-name
description: A description of what this skill does and when to use it.
---
```

With optional fields:

```yaml
---
name: pdf-processing
description: Extract text and tables from PDF files, fill forms, merge documents.
license: Apache-2.0
metadata:
  author: example-org
  version: "1.0"
---
```

### Field Reference

| Field | Required | Constraints |
|-------|----------|-------------|
| `name` | Yes | Max 64 characters. Lowercase letters, numbers, and hyphens only. Must not start or end with a hyphen. |
| `description` | Yes | Max 1024 characters. Non-empty. Describes what the skill does and when to use it. |
| `license` | No | License name or reference to a bundled license file. |
| `compatibility` | No | Max 500 characters. Indicates environment requirements (intended product, system packages, network access, etc.). |
| `metadata` | No | Arbitrary key-value mapping for additional metadata. |
| `allowed-tools` | No | Space-delimited list of pre-approved tools the skill may use. (Experimental) |

### Name Field Rules

- Must be 1-64 characters
- May only contain unicode lowercase alphanumeric characters and hyphens (`a-z` and `-`)
- Must not start or end with `-`
- Must not contain consecutive hyphens (`--`)
- Must match the parent directory name

**Valid examples:**
```yaml
name: pdf-processing
name: data-analysis
name: code-review
```

**Invalid examples:**
```yaml
name: PDF-Processing  # uppercase not allowed
name: -pdf            # cannot start with hyphen
name: pdf--processing # consecutive hyphens not allowed
```

### Description Best Practices

Good example:
```yaml
description: Extracts text and tables from PDF files, fills PDF forms, and merges multiple PDFs. Use when working with PDF documents or when the user mentions PDFs, forms, or document extraction.
```

Poor example:
```yaml
description: Helps with PDFs.
```

---

## Optional Directories

### scripts/

Contains executable code that agents can run. Scripts should:
- Be self-contained or clearly document dependencies
- Include helpful error messages
- Handle edge cases gracefully

Supported languages depend on the agent implementation. Common options include Python, Bash, and JavaScript.

### references/

Contains additional documentation that agents can read when needed:
- `REFERENCE.md` - Detailed technical reference
- `FORMS.md` - Form templates or structured data formats
- Domain-specific files (`finance.md`, `legal.md`, etc.)

Keep individual reference files focused. Agents load these on demand, so smaller files mean less use of context.

### assets/

Contains static resources:
- Templates (document templates, configuration templates)
- Images (diagrams, examples)
- Data files (lookup tables, schemas)

---

## Integrating Skills

### Integration Approaches

**Filesystem-based agents** operate within a computer environment (bash/unix) and represent the most capable option. Skills are activated when models issue shell commands like `cat /path/to/my-skill/SKILL.md`.

**Tool-based agents** function without a dedicated computer environment. Instead, they implement tools allowing models to trigger skills and access bundled assets.

### Agent Implementation Overview

A skills-compatible agent needs to:

1. **Discover** skills in configured directories
2. **Load metadata** (name and description) at startup
3. **Match** user tasks to relevant skills
4. **Activate** skills by loading full instructions
5. **Execute** scripts and access resources as needed

### Injecting into Context

For Claude models, the recommended format uses XML:

```xml
<available_skills>
  <skill>
    <name>pdf-processing</name>
    <description>Extracts text and tables from PDF files, fills forms, merges documents.</description>
    <location>/path/to/skills/pdf-processing/SKILL.md</location>
  </skill>
  <skill>
    <name>data-analysis</name>
    <description>Analyzes datasets, generates charts, and creates summary reports.</description>
    <location>/path/to/skills/data-analysis/SKILL.md</location>
  </skill>
</available_skills>
```

Keep metadata concise. Each skill should add roughly 50-100 tokens to the context.

---

## Example: PDF Skill

```yaml
---
name: pdf-processing
description: Extract text and tables from PDF files, fill forms, merge documents.
---

# PDF Processing

## When to use this skill
Use this skill when the user needs to work with PDF files...

## How to extract text
1. Use pdfplumber for text extraction...

## How to fill forms
See [forms.md](references/forms.md) for detailed instructions.
```

---

## Security Considerations

Skills provide Claude with new capabilities through instructions and code. Recommendations:

- **Sandboxing**: Run scripts in isolated environments
- **Allowlisting**: Only execute scripts from trusted skills
- **Confirmation**: Ask users before running potentially dangerous operations
- **Logging**: Record all script executions for auditing

Install skills only from trusted sources. When installing a skill from a less-trusted source, thoroughly audit it before use.

---

## Validation

Use the [skills-ref](https://github.com/agentskills/agentskills/tree/main/skills-ref) reference library to validate your skills:

```bash
# Validate a skill directory
skills-ref validate ./my-skill

# Generate <available_skills> XML for agent prompts
skills-ref to-prompt <path>...
```

---

## Supported Platforms

Claude Code, Claude.ai, GitHub, Cursor, VS Code, OpenAI Codex, Gemini CLI, Goose, Letta, OpenCode, Amp, Factory

---

## Timeline

- **October 16, 2025**: Anthropic released Agent Skills
- **December 18, 2025**: Published as open standard at https://agentskills.io

---

## Reference Links

### Official Specification
- https://agentskills.io/home
- https://agentskills.io/specification
- https://agentskills.io/what-are-skills
- https://agentskills.io/integrate-skills

### Anthropic Implementation
- https://github.com/anthropics/skills
- https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills

### GitHub Specification
- https://github.com/agentskills/agentskills
- https://github.com/agentskills/agentskills/tree/main/skills-ref
