---
name: market-intel
description: Research and analyze market intelligence using web sources to generate professional intelligence reports. Use when user needs competitor analysis, market trends, or product research.
tags: [research, market, intelligence, web, analysis, competitive]
version: 1.0.0
---

## Quick Start - How to Execute

**AI agents must use built-in WebSearch/WebFetch tools and execute analysis script, then write HTML report.**

### 2-Step Workflow

**Step 1: Analyze Web Data** (Execute script)
```bash
python3 /skills/market-intel/scripts/analyze_research.py \
  --input /workspace/search_results.json \
  --output /workspace/analysis.json
```

**Step 2: Generate HTML Report** (Use Write tool)
- Read `/workspace/analysis.json`
- Use Write tool to create professional HTML report at `/workspace/market_report.html`
- Include: executive summary, key insights, entity tables, sentiment analysis, topic breakdown

### Path Notes
- Skill scripts: `/skills/market-intel/scripts/`
- Workspace files: `/workspace/`
- Use these exact paths when executing

---

# Market Intelligence Skill

Quick web research → automated analysis → professional reports.

## When to Use

Use this skill when the user needs to:
- Analyze competitors and market positioning
- Research product features and reviews
- Identify market trends and patterns
- Map technology landscapes
- Generate intelligence reports

## How It Works

This skill demonstrates coordination between built-in tools, Python scripts, and file operations:

1. **Agent uses WebSearch/WebFetch** to gather information from the web
2. **analyze_research.py** processes results to extract entities, sentiment, and topics
3. **Agent uses Write tool** to create professional HTML report from analysis data

## Why Script Execution is Required

The analyze_research.py script performs operations AI cannot do efficiently:
- **Natural Language Processing**: Sentiment analysis and entity extraction
- **Statistical Aggregation**: Frequency analysis and topic clustering
- **Structured Output**: JSON data processing and transformation

**This skill demonstrates tool → script → tool coordination** - the AI uses WebSearch, runs analysis script, then uses Write tool for the final report.

## Usage Examples

```bash
# After WebSearch saves results, analyze them
python3 /skills/market-intel/scripts/analyze_research.py \
  --input /workspace/search_results.json \
  --output /workspace/analysis.json

# Then agent reads analysis.json and uses Write tool to create HTML report
```

## Script Reference

### analyze_research.py

**Purpose**: Extract intelligence from web search results

**Input**: `search_results.json` (from WebSearch tool)
- Format: JSON with query and results array
- Contains titles, URLs, snippets, dates

**Output**: `analysis.json` (~2-3KB)
- Entities: companies, products, people
- Sentiment: positive/negative/neutral counts
- Topics: themes with mention counts
- Insights: human-readable findings

**Arguments**:
- `--input`: Path to search results JSON
- `--output`: Path for analysis output

## HTML Report Format

After running analyze_research.py, agent should use Write tool to create HTML report with:

**Required Sections**:
- Executive Summary (from insights)
- Key Insights (bulleted list)
- Entity Analysis (table with companies, products, people)
- Sentiment Analysis (table with counts and percentages)
- Topic Analysis (table with topics, mentions, sentiment)

**Styling**: Include inline CSS for professional appearance (tables, colors, responsive design)

## Dependencies

- Python 3.11+
- Standard library only (no external packages)
