#!/usr/bin/env python3
"""Extract text from PDF files using pypdf."""

import sys
from pathlib import Path


def extract_text(pdf_path: str) -> str:
    """Extract text from a PDF file.

    Args:
        pdf_path: Path to the PDF file.

    Returns:
        Extracted text content.
    """
    try:
        from pypdf import PdfReader
    except ImportError:
        return "Error: pypdf not installed. Run: uv pip install pypdf"

    path = Path(pdf_path)
    if not path.exists():
        return f"Error: File not found: {pdf_path}"

    if not path.suffix.lower() == ".pdf":
        return f"Error: Not a PDF file: {pdf_path}"

    try:
        reader = PdfReader(path)
        text_parts = []

        for i, page in enumerate(reader.pages, 1):
            page_text = page.extract_text()
            if page_text:
                text_parts.append(f"--- Page {i} ---\n{page_text}")

        if not text_parts:
            return "Warning: No text content found in PDF."

        return "\n\n".join(text_parts)

    except Exception as e:
        return f"Error extracting text: {e}"


def main():
    """CLI entry point."""
    if len(sys.argv) < 2:
        print("Usage: python extract_text.py <input.pdf>")
        print("Example: python extract_text.py document.pdf")
        sys.exit(1)

    pdf_path = sys.argv[1]
    result = extract_text(pdf_path)
    print(result)


if __name__ == "__main__":
    main()
