#!/usr/bin/env python3
"""
Report Generator Script
Generates structured reports from JSON/CSV data in multiple formats.
"""

import json
import csv
import argparse
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional


def load_json_data(input_path: Path) -> List[Dict[str, Any]]:
    """Load data from JSON file."""
    try:
        with open(input_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Expect a 'records' key with list of objects
        if isinstance(data, dict) and 'records' in data:
            return data['records']
        elif isinstance(data, list):
            return data
        else:
            raise ValueError("JSON must contain 'records' array or be a list")
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON format: {e}")


def load_csv_data(input_path: Path) -> List[Dict[str, Any]]:
    """Load data from CSV file."""
    try:
        with open(input_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            data = list(reader)

        # Convert numeric strings to numbers
        for row in data:
            for key, value in row.items():
                try:
                    # Try to convert to int first
                    if '.' not in value:
                        row[key] = int(value)
                    else:
                        row[key] = float(value)
                except (ValueError, AttributeError):
                    # Keep as string if conversion fails
                    pass

        return data
    except Exception as e:
        raise ValueError(f"Invalid CSV format: {e}")


def load_data(input_path: Path) -> List[Dict[str, Any]]:
    """Load data from JSON or CSV file based on extension."""
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    suffix = input_path.suffix.lower()

    if suffix == '.json':
        return load_json_data(input_path)
    elif suffix == '.csv':
        return load_csv_data(input_path)
    else:
        raise ValueError(f"Unsupported file format: {suffix}. Use .json or .csv")


def aggregate_data(data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Calculate statistics from data."""
    if not data:
        return {
            'count': 0,
            'numeric_fields': {}
        }

    stats = {
        'count': len(data),
        'numeric_fields': {}
    }

    # Find numeric fields
    numeric_fields = {}
    for row in data:
        for key, value in row.items():
            if isinstance(value, (int, float)):
                if key not in numeric_fields:
                    numeric_fields[key] = []
                numeric_fields[key].append(value)

    # Calculate statistics for each numeric field
    for field, values in numeric_fields.items():
        stats['numeric_fields'][field] = {
            'sum': sum(values),
            'average': sum(values) / len(values),
            'min': min(values),
            'max': max(values),
            'count': len(values)
        }

    return stats


def load_template(template_path: Path) -> str:
    """Load HTML template from file."""
    if not template_path.exists():
        raise FileNotFoundError(f"Template file not found: {template_path}")

    try:
        with open(template_path, 'r', encoding='utf-8') as f:
            template = f.read()

        # Verify required placeholders
        required_placeholders = ['{{TITLE}}', '{{DATA}}', '{{SUMMARY}}', '{{TIMESTAMP}}']
        missing = [p for p in required_placeholders if p not in template]
        if missing:
            raise ValueError(f"Template missing required placeholders: {', '.join(missing)}")

        return template
    except Exception as e:
        raise ValueError(f"Error loading template: {e}")


def generate_markdown(data: List[Dict[str, Any]], title: str) -> str:
    """Generate Markdown report."""
    if not data:
        return f"# {title}\n\n*No data to report*\n"

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    stats = aggregate_data(data)

    # Build markdown
    lines = [
        f"# {title}",
        f"",
        f"*Generated: {timestamp}*",
        f"",
        f"## Summary",
        f"",
        f"- **Total Records**: {stats['count']}",
    ]

    # Add numeric field statistics
    if stats['numeric_fields']:
        lines.append(f"")
        lines.append(f"### Statistics")
        lines.append(f"")
        for field, field_stats in stats['numeric_fields'].items():
            lines.append(f"**{field}**:")
            lines.append(f"- Sum: {field_stats['sum']:.2f}")
            lines.append(f"- Average: {field_stats['average']:.2f}")
            lines.append(f"- Min: {field_stats['min']:.2f}")
            lines.append(f"- Max: {field_stats['max']:.2f}")
            lines.append(f"")

    # Add data table
    lines.append(f"## Data")
    lines.append(f"")

    # Get all keys from first record
    keys = list(data[0].keys())

    # Table header
    lines.append("| " + " | ".join(keys) + " |")
    lines.append("| " + " | ".join(["---"] * len(keys)) + " |")

    # Table rows
    for row in data:
        values = [str(row.get(key, '')) for key in keys]
        lines.append("| " + " | ".join(values) + " |")

    return "\n".join(lines)


def generate_html(data: List[Dict[str, Any]], title: str, template: Optional[str] = None) -> str:
    """Generate HTML report."""
    if not data:
        return f"<html><body><h1>{title}</h1><p>No data to report</p></body></html>"

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    stats = aggregate_data(data)

    # Generate summary HTML
    summary_lines = [f"<p><strong>Total Records:</strong> {stats['count']}</p>"]

    if stats['numeric_fields']:
        summary_lines.append("<h3>Statistics</h3>")
        for field, field_stats in stats['numeric_fields'].items():
            summary_lines.append(f"<div class='stat-card'>")
            summary_lines.append(f"  <h4>{field}</h4>")
            summary_lines.append(f"  <p>Sum: {field_stats['sum']:.2f}</p>")
            summary_lines.append(f"  <p>Average: {field_stats['average']:.2f}</p>")
            summary_lines.append(f"  <p>Range: {field_stats['min']:.2f} - {field_stats['max']:.2f}</p>")
            summary_lines.append(f"</div>")

    summary_html = "\n".join(summary_lines)

    # Generate data table HTML
    keys = list(data[0].keys())

    table_lines = ["<table>", "<thead><tr>"]
    for key in keys:
        table_lines.append(f"<th>{key}</th>")
    table_lines.append("</tr></thead>")
    table_lines.append("<tbody>")

    for row in data:
        table_lines.append("<tr>")
        for key in keys:
            value = row.get(key, '')
            table_lines.append(f"<td>{value}</td>")
        table_lines.append("</tr>")

    table_lines.append("</tbody></table>")
    data_html = "\n".join(table_lines)

    # Use template if provided
    if template:
        html = template.replace('{{TITLE}}', title)
        html = html.replace('{{TIMESTAMP}}', timestamp)
        html = html.replace('{{SUMMARY}}', summary_html)
        html = html.replace('{{DATA}}', data_html)
        return html

    # Generate basic HTML without template
    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        h1 {{
            color: #333;
            border-bottom: 3px solid #007bff;
            padding-bottom: 10px;
        }}
        .timestamp {{
            color: #666;
            font-style: italic;
            margin-bottom: 20px;
        }}
        .summary {{
            background: white;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .stat-card {{
            display: inline-block;
            background: #f8f9fa;
            padding: 15px;
            margin: 10px;
            border-radius: 5px;
            border-left: 4px solid #007bff;
        }}
        .stat-card h4 {{
            margin: 0 0 10px 0;
            color: #007bff;
        }}
        .stat-card p {{
            margin: 5px 0;
            font-size: 14px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            background: white;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        th {{
            background-color: #007bff;
            color: white;
            padding: 12px;
            text-align: left;
        }}
        td {{
            padding: 10px 12px;
            border-bottom: 1px solid #ddd;
        }}
        tr:nth-child(even) {{
            background-color: #f8f9fa;
        }}
        tr:hover {{
            background-color: #e9ecef;
        }}
    </style>
</head>
<body>
    <h1>{title}</h1>
    <div class="timestamp">Generated: {timestamp}</div>
    <div class="summary">
        <h2>Summary</h2>
        {summary_html}
    </div>
    <h2>Data</h2>
    {data_html}
</body>
</html>"""

    return html


def generate_json(data: List[Dict[str, Any]], title: str) -> str:
    """Generate JSON report with statistics."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    stats = aggregate_data(data)

    report = {
        'title': title,
        'generated': timestamp,
        'format_version': '1.0',
        'summary': {
            'total_records': stats['count'],
            'statistics': stats['numeric_fields']
        },
        'data': data
    }

    return json.dumps(report, indent=2)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Generate structured reports from JSON or CSV data'
    )
    parser.add_argument(
        '--input',
        required=True,
        help='Path to input data file (JSON or CSV)'
    )
    parser.add_argument(
        '--output',
        required=True,
        help='Path for output report file'
    )
    parser.add_argument(
        '--format',
        choices=['markdown', 'html', 'json'],
        default='markdown',
        help='Output format (default: markdown)'
    )
    parser.add_argument(
        '--template',
        help='Path to HTML template file (optional, for HTML format only)'
    )
    parser.add_argument(
        '--title',
        default='Data Report',
        help='Report title (default: Data Report)'
    )

    args = parser.parse_args()

    try:
        # Convert to Path objects
        input_path = Path(args.input)
        output_path = Path(args.output)

        # Load data
        try:
            data = load_data(input_path)
        except FileNotFoundError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(2)

        # Load template if specified
        template = None
        if args.template:
            if args.format != 'html':
                print("Warning: --template is only used with --format html", file=sys.stderr)
            else:
                try:
                    template = load_template(Path(args.template))
                except (FileNotFoundError, ValueError) as e:
                    print(f"Error: {e}", file=sys.stderr)
                    sys.exit(3)

        # Generate report based on format
        if args.format == 'markdown':
            content = generate_markdown(data, args.title)
        elif args.format == 'html':
            content = generate_html(data, args.title, template)
        elif args.format == 'json':
            content = generate_json(data, args.title)
        else:
            print(f"Error: Unsupported format: {args.format}", file=sys.stderr)
            sys.exit(2)

        # Write output
        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(content)

            print(f"Report generated successfully: {output_path}")
            sys.exit(0)

        except Exception as e:
            print(f"Error writing output file: {e}", file=sys.stderr)
            sys.exit(1)

    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
