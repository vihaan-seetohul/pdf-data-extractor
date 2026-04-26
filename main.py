"""
Run the extractor on all sample PDFs, validate results, export to all formats.
"""

import json
from pathlib import Path

from src.extractor import extract_invoice
from src.validators import validate_invoice
from src.exporters import export_all


def main():
    samples_dir = Path("samples")
    if not samples_dir.exists():
        print("No samples/ directory found. Run sample_generator.py first.")
        return

    pdf_files = sorted(samples_dir.glob("*.pdf"))
    if not pdf_files:
        print(f"No PDFs found in {samples_dir}/")
        return

    print(f"Found {len(pdf_files)} PDFs to process.\n")

    extractions = []
    all_passed = 0
    all_warnings = 0
    all_errors = 0

    for pdf_file in pdf_files:
        print("-" * 70)
        result = extract_invoice(pdf_file)
        validation = validate_invoice(result)
        extractions.append(result)

        # Print compact summary per file
        print(f"  File: {result['source_file']}")
        print(f"  Invoice #: {result.get('invoice_number')}")
        print(f"  Vendor: {result.get('vendor_name')}")
        print(f"  Customer: {result.get('customer_name')}")
        print(f"  Total: ${result.get('total'):,.2f}" if result.get("total") else "  Total: N/A")
        print(f"  Line items: {len(result.get('line_items') or [])}")
        print(f"  Validation: {validation['summary']}")

        for check in validation["checks"]:
            print(f"    [{check['severity'].upper()}] {check['field']}: {check['message']}")

        if validation["is_valid"]:
            all_passed += 1
        all_errors += validation["error_count"]
        all_warnings += validation["warning_count"]

    print("=" * 70)
    print(f"Validation summary: {all_passed}/{len(pdf_files)} passed | "
          f"{all_errors} errors, {all_warnings} warnings")
    print()

    # Export to all formats
    print("Exporting to output/ ...")
    paths = export_all(extractions, output_dir="output", base_name="invoices")
    print()
    for fmt, path in paths.items():
        print(f"  {fmt}: {path}")
    print()
    print("Done.")


if __name__ == "__main__":
    main()