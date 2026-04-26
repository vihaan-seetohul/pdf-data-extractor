# PDF Invoice Data Extractor

A production-style Python tool that extracts structured data from invoice PDFs into JSON, CSV, and Excel formats. Built to handle multiple invoice layouts with defensive parsing, validation, and graceful error handling.

## What it does

Given any PDF invoice, this tool extracts:

- **Header fields** — invoice number, issue date, due date
- **Parties** — vendor and customer names
- **Line items** — description, SKU, quantity, unit price, line total
- **Totals** — subtotal, tax, total
- **Validation** — sanity-checks math (line items sum, subtotal + tax = total) and date logic

Output is delivered in **four formats simultaneously**: JSON for developers, two CSV layouts (summary + line items), and a styled Excel workbook with three sheets.

## Why this exists

Most PDF extraction tools handle one specific invoice format and break on anything else. This project demonstrates the engineering required to handle real-world variation — different layouts, different label phrasings, columnar text rendering — without losing data quality.

The code uses a multi-strategy approach:

1. **pdfplumber** for primary extraction (best for digital PDFs with structured tables)
2. **PyMuPDF** as a fallback for PDFs where pdfplumber returns nothing
3. **Text-based pattern matching** as a third fallback when table detection fails (common with column-based layouts)

A validation layer runs after extraction to flag missing fields, math inconsistencies, and unusual values — before the data ever reaches downstream systems.

## Demonstrated capabilities

Tested against 6 sample invoices across 3 distinct layouts:

| Layout | Description | Extraction Method | Result |
|---|---|---|---|
| Classic | Standard header with structured table | pdfplumber direct | All fields extracted |
| Modern | FROM/TO column layout, cleaner styling | pdfplumber + text fallback | All fields extracted |
| Compact | Inline metadata, tighter formatting | pdfplumber direct | All fields extracted |

**6/6 invoices pass validation with zero errors and zero warnings** after extraction.

## Architecture