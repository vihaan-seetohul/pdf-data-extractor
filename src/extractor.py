"""
Core PDF extraction engine.

Strategy:
1. Try pdfplumber first - good at text + tables for digital PDFs
2. Fall back to PyMuPDF if pdfplumber returns nothing useful
3. For line items: try table extraction first, fall back to text-based extraction

Returns a structured dict with all extracted fields.
"""

import logging
from pathlib import Path

import pdfplumber
import fitz  # PyMuPDF

from src.parsers import (
    parse_invoice_number,
    parse_dates,
    parse_totals,
    parse_parties,
    parse_line_items_from_table,
    parse_line_items_from_text,
)

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def extract_with_pdfplumber(pdf_path):
    """Use pdfplumber to extract text and tables."""
    raw_text = ""
    all_tables = []

    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text() or ""
            raw_text += page_text + "\n"

            tables = page.extract_tables()
            if tables:
                all_tables.extend(tables)

    return raw_text, all_tables


def extract_with_pymupdf(pdf_path):
    """Fall back to PyMuPDF for text extraction."""
    raw_text = ""
    with fitz.open(pdf_path) as doc:
        for page in doc:
            raw_text += page.get_text() + "\n"
    return raw_text, []


def extract_invoice(pdf_path):
    """Extract structured data from an invoice PDF."""
    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    logger.info(f"Extracting: {pdf_path.name}")

    try:
        raw_text, tables = extract_with_pdfplumber(pdf_path)
        method = "pdfplumber"
    except Exception as exc:
        logger.warning(f"pdfplumber failed for {pdf_path.name}: {exc}")
        raw_text, tables = "", []
        method = "pdfplumber-failed"

    if not raw_text.strip():
        try:
            raw_text, tables = extract_with_pymupdf(pdf_path)
            method = "pymupdf"
        except Exception as exc:
            logger.error(f"PyMuPDF also failed for {pdf_path.name}: {exc}")
            return _empty_result(pdf_path, "all-methods-failed")

    if not raw_text.strip():
        logger.warning(f"No text extracted from {pdf_path.name}")
        return _empty_result(pdf_path, method)

    invoice_number = parse_invoice_number(raw_text)
    issue_date, due_date = parse_dates(raw_text)
    vendor_name, customer_name = parse_parties(raw_text)
    totals = parse_totals(raw_text)

    # Try table-based line item extraction first
    line_items = []
    if tables:
        largest_table = max(tables, key=len)
        line_items = parse_line_items_from_table(largest_table)

    # Fallback: text-based extraction if tables found nothing
    if not line_items:
        line_items = parse_line_items_from_text(raw_text)
        if line_items:
            method += "+text-fallback"

    return {
        "source_file": pdf_path.name,
        "invoice_number": invoice_number,
        "issue_date": issue_date,
        "due_date": due_date,
        "vendor_name": vendor_name,
        "customer_name": customer_name,
        "line_items": line_items,
        "subtotal": totals["subtotal"],
        "tax": totals["tax"],
        "total": totals["total"],
        "extraction_method": method,
        "raw_text_length": len(raw_text),
    }


def _empty_result(pdf_path, method):
    return {
        "source_file": pdf_path.name,
        "invoice_number": None,
        "issue_date": None,
        "due_date": None,
        "vendor_name": None,
        "customer_name": None,
        "line_items": [],
        "subtotal": None,
        "tax": None,
        "total": None,
        "extraction_method": method,
        "raw_text_length": 0,
    }