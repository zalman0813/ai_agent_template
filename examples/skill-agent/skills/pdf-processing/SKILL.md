---
name: pdf-processing
description: Extract text and tables from PDF files. Use when user mentions PDF, extract, or document processing.
---

# PDF Processing Skill

This skill provides PDF text extraction capabilities.

## Usage

Run the extraction script:
```bash
python scripts/extract_text.py <input.pdf>
```

## Output

The script outputs extracted text to stdout. You can redirect to a file:
```bash
python scripts/extract_text.py document.pdf > output.txt
```

## Requirements

- pypdf library (install with `uv pip install pypdf`)
