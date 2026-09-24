"""
Extract text from PDFs for absorb skill.

Usage:
    python tools/extract_pdf.py raw/sources/paper.pdf
    python tools/extract_pdf.py raw/sources/paper.pdf --output wiki/notes/paper.md
"""
import sys
import argparse
from pathlib import Path
from PyPDF2 import PdfReader

def extract_pdf(pdf_path: Path, output_path: Path | None = None, max_pages: int = 50) -> str:
    """Extract text from PDF."""
    if not pdf_path.exists():
        print(f"File not found: {pdf_path}")
        sys.exit(1)
    
    reader = PdfReader(str(pdf_path))
    total_pages = len(reader.pages)
    print(f"Reading {pdf_path.name}: {total_pages} pages")
    
    # Try extracting text
    text_parts = []
    for i, page in enumerate(reader.pages[:max_pages]):
        text = page.extract_text()
        if text and text.strip():
            text_parts.append(f"### Page {i+1}\n\n{text}\n")
    
    if not text_parts:
        print(f"WARNING: No extractable text. This may be a scanned PDF.")
        print("For scanned PDFs, use OCR or write chapter notes manually.")
        return ""
    
    full_text = "\n".join(text_parts)
    print(f"Extracted {len(full_text)} chars from {len(text_parts)} pages")
    
    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(full_text, encoding="utf-8")
        print(f"Wrote to: {output_path}")
    
    return full_text

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extract text from PDF")
    parser.add_argument("pdf", type=Path, help="PDF file to extract")
    parser.add_argument("--output", "-o", type=Path, help="Output markdown file")
    parser.add_argument("--max-pages", type=int, default=50, help="Max pages to extract")
    args = parser.parse_args()
    
    extract_pdf(args.pdf, args.output, args.max_pages)