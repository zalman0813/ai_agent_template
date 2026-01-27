#!/usr/bin/env python3
"""Generate PDF from Markdown content.

Usage:
    python3 generate_pdf.py --input content.md --output content.pdf [--title "Title"] [--author "Author"]

Dependencies:
    - markdown2: Markdown to HTML conversion
    - weasyprint: HTML to PDF rendering
"""

import argparse
import sys
from pathlib import Path

try:
    import markdown2
    from weasyprint import HTML, CSS
except ImportError as e:
    print(f"Error: Missing dependency - {e}")
    print("Install with: pip install markdown2 weasyprint")
    sys.exit(1)


# Professional CSS styling for PDF output
PDF_STYLES = """
@page {
    size: A4;
    margin: 2.5cm 2cm;

    @bottom-center {
        content: counter(page);
        font-size: 10pt;
        color: #666;
    }
}

body {
    font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
    font-size: 11pt;
    line-height: 1.6;
    color: #333;
    max-width: 100%;
}

/* Title page styling */
.title-page {
    text-align: center;
    padding-top: 30%;
    page-break-after: always;
}

.title-page h1 {
    font-size: 28pt;
    margin-bottom: 1em;
    color: #1a1a1a;
}

.title-page .author {
    font-size: 14pt;
    color: #666;
    margin-top: 2em;
}

.title-page .date {
    font-size: 12pt;
    color: #888;
    margin-top: 1em;
}

/* Headings */
h1 {
    font-size: 20pt;
    color: #1a1a1a;
    border-bottom: 2px solid #e0e0e0;
    padding-bottom: 0.3em;
    margin-top: 1.5em;
    margin-bottom: 0.8em;
}

h2 {
    font-size: 16pt;
    color: #2c2c2c;
    margin-top: 1.3em;
    margin-bottom: 0.6em;
}

h3 {
    font-size: 13pt;
    color: #3c3c3c;
    margin-top: 1.1em;
    margin-bottom: 0.5em;
}

/* Paragraphs */
p {
    margin-bottom: 0.8em;
    text-align: justify;
}

/* Code blocks */
pre {
    background-color: #f5f5f5;
    border: 1px solid #e0e0e0;
    border-radius: 4px;
    padding: 1em;
    font-family: 'Monaco', 'Menlo', 'Consolas', monospace;
    font-size: 9pt;
    line-height: 1.4;
    overflow-x: auto;
    margin: 1em 0;
}

code {
    font-family: 'Monaco', 'Menlo', 'Consolas', monospace;
    font-size: 9pt;
    background-color: #f0f0f0;
    padding: 0.2em 0.4em;
    border-radius: 3px;
}

pre code {
    background-color: transparent;
    padding: 0;
}

/* Tables */
table {
    width: 100%;
    border-collapse: collapse;
    margin: 1em 0;
    font-size: 10pt;
}

th, td {
    border: 1px solid #ddd;
    padding: 0.6em 0.8em;
    text-align: left;
}

th {
    background-color: #f5f5f5;
    font-weight: bold;
}

tr:nth-child(even) {
    background-color: #fafafa;
}

/* Lists */
ul, ol {
    margin: 0.8em 0;
    padding-left: 2em;
}

li {
    margin-bottom: 0.4em;
}

/* Blockquotes */
blockquote {
    border-left: 4px solid #ddd;
    margin: 1em 0;
    padding: 0.5em 1em;
    color: #666;
    background-color: #fafafa;
}

/* Links */
a {
    color: #0066cc;
    text-decoration: none;
}

/* Horizontal rule */
hr {
    border: none;
    border-top: 1px solid #e0e0e0;
    margin: 2em 0;
}
"""


def convert_markdown_to_html(markdown_content: str, title: str | None = None, author: str | None = None) -> str:
    """Convert Markdown content to HTML with styling.

    Args:
        markdown_content: Raw Markdown text
        title: Optional document title for title page
        author: Optional author name for title page

    Returns:
        Complete HTML document string
    """
    # Convert Markdown to HTML with extensions
    html_content = markdown2.markdown(
        markdown_content,
        extras=[
            "fenced-code-blocks",
            "tables",
            "code-friendly",
            "cuddled-lists",
            "header-ids",
        ]
    )

    # Build title page if title is provided
    title_page = ""
    if title:
        from datetime import datetime
        date_str = datetime.now().strftime("%Y-%m-%d")
        author_html = f'<p class="author">{author}</p>' if author else ""
        title_page = f'''
        <div class="title-page">
            <h1>{title}</h1>
            {author_html}
            <p class="date">{date_str}</p>
        </div>
        '''

    # Wrap in complete HTML document
    html_document = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>{title or 'Document'}</title>
</head>
<body>
    {title_page}
    {html_content}
</body>
</html>"""

    return html_document


def generate_pdf(input_path: Path, output_path: Path, title: str | None = None, author: str | None = None) -> None:
    """Generate PDF from Markdown file.

    Args:
        input_path: Path to input Markdown file
        output_path: Path for output PDF file
        title: Optional document title
        author: Optional author name
    """
    # Read Markdown content
    markdown_content = input_path.read_text(encoding="utf-8")

    # Convert to HTML
    html_content = convert_markdown_to_html(markdown_content, title, author)

    # Generate PDF with WeasyPrint
    html_doc = HTML(string=html_content)
    css = CSS(string=PDF_STYLES)

    html_doc.write_pdf(output_path, stylesheets=[css])

    print(f"PDF generated: {output_path}")
    print(f"  Input: {input_path}")
    if title:
        print(f"  Title: {title}")
    if author:
        print(f"  Author: {author}")


def main():
    parser = argparse.ArgumentParser(
        description="Generate PDF from Markdown content",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 generate_pdf.py --input content.md --output content.pdf
  python3 generate_pdf.py -i content.md -o report.pdf --title "My Report" --author "John Doe"
        """
    )

    parser.add_argument(
        "--input", "-i",
        type=Path,
        required=True,
        help="Input Markdown file path"
    )
    parser.add_argument(
        "--output", "-o",
        type=Path,
        required=True,
        help="Output PDF file path"
    )
    parser.add_argument(
        "--title", "-t",
        type=str,
        default=None,
        help="Document title (creates title page)"
    )
    parser.add_argument(
        "--author", "-a",
        type=str,
        default=None,
        help="Author name (shown on title page)"
    )

    args = parser.parse_args()

    # Validate input file
    if not args.input.exists():
        print(f"Error: Input file not found: {args.input}")
        sys.exit(1)

    # Create output directory if needed
    args.output.parent.mkdir(parents=True, exist_ok=True)

    # Generate PDF
    try:
        generate_pdf(args.input, args.output, args.title, args.author)
    except Exception as e:
        print(f"Error generating PDF: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
