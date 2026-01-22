---
name: report-generator
description: Generate structured reports from data files (JSON, CSV) in multiple formats (Markdown, HTML, JSON). Supports templates, custom styling, and data aggregation.
version: 1.0.0
tags: [reporting, data-processing, templates]
---

# Report Generator Skill

## Overview

The Report Generator skill creates structured, formatted reports from data files. It supports multiple input formats (JSON, CSV) and can generate outputs in Markdown, HTML, or JSON format with optional custom templates and styling.

## When to Use This Skill

Use the report-generator skill when you need to:

- Generate professional reports from structured data files
- Convert data between formats (CSV to HTML, JSON to Markdown, etc.)
- Create documentation from data with consistent formatting
- Apply custom templates for branded report output
- Aggregate and summarize data with statistics
- Produce multiple report formats from the same data source

## How It Works

The skill follows this workflow:

1. **Data Loading**: Reads input data from JSON or CSV files
2. **Data Processing**: Aggregates statistics (count, sum, average) from numeric fields
3. **Template Application**: Applies custom templates from the references directory (optional)
4. **Report Generation**: Creates formatted output in the specified format
5. **Output Writing**: Saves the generated report to the specified location

## Usage

### Basic Usage

Generate a Markdown report from JSON data:

```bash
python3 /skills/report-generator/scripts/generate_report.py \
  --input /workspace/data.json \
  --output /workspace/report.md \
  --format markdown \
  --title "My Data Report"
```

### Using Custom Templates

Generate an HTML report with a custom template:

```bash
python3 /skills/report-generator/scripts/generate_report.py \
  --input /workspace/sales_data.csv \
  --output /workspace/sales_report.html \
  --format html \
  --template /skills/report-generator/references/report_template.html \
  --title "Q4 Sales Report"
```

### Multiple Output Formats

The skill supports three output formats:

**Markdown** (default):
```bash
--format markdown
```
Generates clean, readable Markdown with tables and statistics.

**HTML**:
```bash
--format html
```
Generates styled HTML with embedded CSS. Use `--template` for custom styling.

**JSON**:
```bash
--format json
```
Generates structured JSON with data and computed statistics.

## Script Parameters

- `--input` (required): Path to input data file (JSON or CSV)
- `--output` (required): Path for output report file
- `--format`: Output format - `markdown`, `html`, or `json` (default: `markdown`)
- `--template`: Path to custom HTML template (optional, HTML format only)
- `--title`: Report title (default: "Data Report")

## Output Formats

### Markdown Format

Generates a structured Markdown document with:
- Report title and timestamp
- Summary statistics section
- Data table with all records
- Aggregated metrics (count, totals, averages)

### HTML Format

Generates a styled HTML document with:
- Responsive design with embedded CSS
- Professional table formatting
- Summary statistics cards
- Mobile-friendly layout
- Custom template support via `--template` parameter

### JSON Format

Generates a structured JSON document with:
- Original data records
- Computed statistics (count, sums, averages)
- Metadata (title, timestamp, format version)

## Reference Files

### Template System

Custom templates are stored in `/skills/report-generator/references/`. For detailed information about creating and using templates, see:

```
/skills/report-generator/references/TEMPLATES.md
```

### Available Templates

**report_template.html**: Professional HTML template with:
- Responsive CSS grid layout
- Summary statistics section
- Data table with alternating row colors
- Print-friendly styling

Templates use placeholder syntax:
- `{{TITLE}}` - Report title
- `{{DATA}}` - Main data table/content
- `{{SUMMARY}}` - Statistics summary section
- `{{TIMESTAMP}}` - Generation timestamp

## Input Data Requirements

### JSON Format

```json
{
  "records": [
    {"id": 1, "name": "Item A", "value": 100, "category": "Type1"},
    {"id": 2, "name": "Item B", "value": 250, "category": "Type2"}
  ]
}
```

The JSON must contain a `records` array with objects.

### CSV Format

```csv
id,name,value,category
1,Item A,100,Type1
2,Item B,250,Type2
```

The CSV must have a header row with column names.

## Data Aggregation

The skill automatically computes statistics for numeric fields:

- **Count**: Total number of records
- **Sum**: Total of all numeric values
- **Average**: Mean of numeric values
- **Min/Max**: Range of numeric values (when applicable)

Statistics are included in all output formats.

## Error Handling

The script provides clear error messages and exit codes:

- **Exit Code 0**: Success
- **Exit Code 1**: File not found or cannot be read
- **Exit Code 2**: Invalid data format or parsing error
- **Exit Code 3**: Template error (missing placeholders, invalid template)

Error messages are written to stderr for easy debugging.

## Examples

### Example 1: Quick CSV to Markdown

```bash
python3 /skills/report-generator/scripts/generate_report.py \
  --input /workspace/products.csv \
  --output /workspace/products_report.md
```

### Example 2: Branded HTML Report

```bash
python3 /skills/report-generator/scripts/generate_report.py \
  --input /workspace/quarterly_data.json \
  --output /workspace/q4_report.html \
  --format html \
  --template /skills/report-generator/references/report_template.html \
  --title "Q4 2024 Performance Report"
```

### Example 3: JSON with Statistics

```bash
python3 /skills/report-generator/scripts/generate_report.py \
  --input /workspace/metrics.csv \
  --output /workspace/metrics_summary.json \
  --format json \
  --title "System Metrics Summary"
```

## Tips for AI Agents

When using this skill, the AI agent should:

1. **Check input files first**: Use `ls` or `read_file` to verify input data exists and is valid
2. **Read documentation**: Review SKILL.md to understand parameters
3. **Choose appropriate format**: Select output format based on user needs (Markdown for readability, HTML for presentation, JSON for further processing)
4. **Use templates**: For professional reports, use the provided HTML template or create custom ones
5. **Verify output**: After generation, read the output file to confirm success and quality
6. **Handle errors**: If the script fails, check the error message and correct the input

## Limitations

- Input files must be valid JSON (with `records` array) or CSV (with header row)
- CSV parsing assumes comma-separated values
- Template substitution is simple string replacement (no complex logic)
- All processing happens in Python standard library (no external dependencies)
- Large files (>100MB) may have performance considerations

## Related Skills

- **file-hash**: Verify data file integrity before processing
- **market-intel**: Fetch external data for report generation

## Version History

- **1.0.0** (2024-01): Initial release with JSON/CSV support, multiple output formats, template system
