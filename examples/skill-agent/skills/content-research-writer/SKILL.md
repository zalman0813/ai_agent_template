---
name: content-research-writer
description: Research topics using web search and produce written content with PDF output. Use for articles, reports, technical documentation, or any content requiring research.
---

# Content Research Writer

A multi-step skill for researching topics and producing professional written content with optional PDF output.

## Workflow Overview

This skill follows a 4-step process:

1. **Create Outline** - Structure the content before writing
2. **Research** - Gather information using web search
3. **Write Content** - Produce the final content in Markdown
4. **Generate PDF** - Convert to professional PDF document

## Step-by-Step Instructions

### Step 1: Create Outline

Create a structured outline for the content:

```
write_file(
    path="/workspace/outline.md",
    content="# [Title]\n\n## 1. Introduction\n- ...\n\n## 2. [Section]\n- ..."
)
```

The outline should include:
- Main title
- Section headings (H2)
- Key points under each section
- Logical flow from introduction to conclusion

### Step 2: Research with Web Search

Use the `duckduckgo_search` tool to gather information:

```
duckduckgo_search(query="[topic] [specific aspect]")
```

**Research tips**:
- Search for each major section of your outline
- Use specific, targeted queries
- Search for recent/current information
- Look for authoritative sources

Save research notes:
```
write_file(
    path="/workspace/research_notes.md",
    content="# Research Notes\n\n## Source 1\n- Key findings...\n\n## Source 2\n- ..."
)
```

### Step 3: Write Content

Create the final content in Markdown format:

```
write_file(
    path="/workspace/content.md",
    content="# [Title]\n\n## Introduction\n\n[Content based on research...]\n\n## [Section 1]\n\n..."
)
```

**Writing guidelines**:
- Follow the outline structure
- Incorporate research findings
- Use proper Markdown formatting
- Include code blocks where appropriate
- Add tables for structured data

### Step 4: Generate PDF (Optional)

Convert Markdown to professional PDF:

```
execute(command="python3 /skills/content-research-writer/scripts/generate_pdf.py --input /workspace/content.md --output /workspace/content.pdf --title 'Your Title' --author 'Author Name'")
```

**Command options**:
- `--input`: Input Markdown file (required)
- `--output`: Output PDF file (required)
- `--title`: Document title (optional)
- `--author`: Author name (optional)

## Output Files

After completing the workflow, the following files will be in `/workspace/`:

| File | Description |
|------|-------------|
| `outline.md` | Content structure and outline |
| `research_notes.md` | Research findings and sources |
| `content.md` | Final written content (Markdown) |
| `content.pdf` | Professional PDF output (if generated) |

## Example Usage

**User request**: "Write a technical article about AI Agent architectures"

**Agent workflow**:
1. Create outline covering: introduction, types of agents, key components, design patterns, conclusion
2. Research each section using web search
3. Write comprehensive content with code examples
4. Generate PDF with professional formatting

## Requirements

- **Web search**: Available via `duckduckgo_search` tool
- **PDF generation**: Requires `markdown2` and `weasyprint` (pre-installed in Docker)

## Tips for Best Results

1. **Be specific in research queries** - "LangChain agent memory types" is better than "AI agents"
2. **Structure content logically** - Use clear headings and subheadings
3. **Include practical examples** - Code snippets, diagrams descriptions, real-world applications
4. **Cite sources** - Reference where information came from
5. **Review before PDF** - Check content.md before generating PDF
