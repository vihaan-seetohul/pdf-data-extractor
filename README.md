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
```
pdf-data-extractor/
├── src/
│   ├── sample_generator.py  # Generates test invoices in multiple layouts
│   ├── extractor.py         # Orchestrator: PDF -> structured data
│   ├── parsers.py           # Pattern matchers for each field
│   ├── validators.py        # Post-extraction sanity checks
│   └── exporters.py         # JSON / CSV / Excel writers
├── samples/                 # Test PDFs (generated)
├── output/                  # Extracted data goes here
├── main.py                  # End-to-end runner
└── requirements.txt
```

Each module has a single responsibility:

## Tech stack

- **Python 3.10+**
- **pdfplumber** — primary PDF text and table extraction
- **PyMuPDF** — fallback PDF reader
- **pandas** — data manipulation
- **openpyxl** — Excel output with styling
- **reportlab** — generating realistic test invoices
- **python-dateutil** — robust date parsing across formats

## Setup

```bash
# Clone and enter the project
git clone https://github.com/vihaan-seetohul/pdf-data-extractor.git
cd pdf-data-extractor

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

## Usage

### Generate test invoices (first time only)

```bash
python3 src/sample_generator.py
```

This creates 6 sample invoices in `samples/` across 3 different layouts.

### Run the extractor

```bash
python3 main.py
```

This processes all PDFs in `samples/`, runs validation on each, and writes outputs to `output/`:

- `invoices.json` — full structured data, all invoices in one file
- `invoices_summary.csv` — one row per invoice (totals only)
- `invoices_line_items.csv` — one row per line item, with invoice metadata repeated
- `invoices.xlsx` — styled multi-sheet workbook (Summary, Line Items, Extraction Notes)

### Use as a library

```python
from src.extractor import extract_invoice
from src.validators import validate_invoice

result = extract_invoice("path/to/your/invoice.pdf")
validation = validate_invoice(result)

print(f"Total: ${result['total']}")
print(f"Validation: {validation['summary']}")
```

## Output example

The JSON output for a successfully extracted invoice:

```json
{
  "source_file": "invoice_001.pdf",
  "invoice_number": "INV-12345",
  "issue_date": "2026-04-09",
  "due_date": "2026-05-09",
  "vendor_name": "Acme Manufacturing Inc.",
  "customer_name": "Globex Corporation",
  "line_items": [
    {
      "description": "Steel mounting bracket",
      "sku": "MNT-204",
      "quantity": 9,
      "unit_price": 45.75,
      "line_total": 411.75
    }
  ],
  "subtotal": 3451.75,
  "tax": 293.40,
  "total": 3745.15,
  "extraction_method": "pdfplumber",
  "raw_text_length": 509
}
```

## Validation checks

After extraction, each invoice is checked for:

- **Required fields present** — invoice number, issue date, total
- **Recommended fields populated** — vendor, customer, due date, subtotal
- **Line item completeness** — description, quantity, line total per row
- **Math consistency** — quantity × unit price = line total, sum of line items = subtotal, subtotal + tax = total
- **Date logic** — due date is after issue date, terms within reasonable range
- **Amount sanity** — totals are positive and within plausible bounds

Each check returns a severity level (error, warning, info) and a message. Errors fail validation; warnings are flagged but don't block output.

## Limitations

This tool is designed for **digital PDFs** (text-based, programmatically generated). It does not yet handle:

- Scanned/image-based PDFs (would require OCR — could be added with pytesseract)
- Multi-page invoices with line items spanning pages
- Currency other than USD (parser currently looks for `$` symbols)
- Invoices in non-English languages

These are addressable extensions, not architectural limitations.

## License

MIT