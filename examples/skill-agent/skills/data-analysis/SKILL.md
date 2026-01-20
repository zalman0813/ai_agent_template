---
name: data-analysis
description: Analyze CSV/JSON data files. Use when user mentions analyze, statistics, or data processing.
---

# Data Analysis Skill

This skill provides basic data analysis for CSV and JSON files.

## Usage

```bash
python scripts/analyze.py <data.csv>
```

## Supported Formats

- CSV files (.csv)
- JSON files (.json)

## Output

The script outputs:
- Basic statistics (count, mean, std, min, max)
- Column information
- Sample data preview

## Requirements

- pandas library (install with `uv pip install pandas`)
