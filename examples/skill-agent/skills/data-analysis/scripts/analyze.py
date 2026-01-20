#!/usr/bin/env python3
"""Analyze CSV/JSON data files using pandas."""

import sys
import json
from pathlib import Path


def analyze_data(file_path: str) -> str:
    """Analyze a data file and return statistics.

    Args:
        file_path: Path to CSV or JSON file.

    Returns:
        Analysis results as formatted string.
    """
    try:
        import pandas as pd
    except ImportError:
        return "Error: pandas not installed. Run: uv pip install pandas"

    path = Path(file_path)
    if not path.exists():
        return f"Error: File not found: {file_path}"

    suffix = path.suffix.lower()

    try:
        # Load data based on file type
        if suffix == ".csv":
            df = pd.read_csv(path)
        elif suffix == ".json":
            df = pd.read_json(path)
        else:
            return f"Error: Unsupported file format: {suffix}. Use .csv or .json"

        # Build analysis report
        lines = [
            f"=== Data Analysis Report ===",
            f"File: {path.name}",
            f"",
            f"--- Shape ---",
            f"Rows: {len(df)}",
            f"Columns: {len(df.columns)}",
            f"",
            f"--- Columns ---",
        ]

        for col in df.columns:
            dtype = df[col].dtype
            null_count = df[col].isnull().sum()
            lines.append(f"  {col}: {dtype} (nulls: {null_count})")

        # Numeric statistics
        numeric_cols = df.select_dtypes(include=["number"]).columns
        if len(numeric_cols) > 0:
            lines.append("")
            lines.append("--- Numeric Statistics ---")
            stats = df[numeric_cols].describe()
            lines.append(stats.to_string())

        # Sample data
        lines.append("")
        lines.append("--- Sample Data (first 5 rows) ---")
        lines.append(df.head().to_string())

        return "\n".join(lines)

    except Exception as e:
        return f"Error analyzing file: {e}"


def main():
    """CLI entry point."""
    if len(sys.argv) < 2:
        print("Usage: python analyze.py <data.csv|data.json>")
        print("Example: python analyze.py sales_data.csv")
        sys.exit(1)

    file_path = sys.argv[1]
    result = analyze_data(file_path)
    print(result)


if __name__ == "__main__":
    main()
