"""
Validation layer for extracted invoice data.

Runs sanity checks on extracted data and flags issues without modifying
the data itself. Output is a list of validation messages by severity.
"""

from datetime import datetime
from dateutil import parser as date_parser


SEVERITY_ERROR = "error"      # data is wrong or missing critical fields
SEVERITY_WARNING = "warning"  # something looks off but not necessarily wrong
SEVERITY_INFO = "info"        # informational notes about the extraction


def validate_invoice(data, tolerance=0.05):
    """
    Run validation checks on extracted invoice data.

    Args:
        data: dict from extract_invoice()
        tolerance: acceptable difference for amount sums (in dollars)

    Returns:
        dict with:
            "is_valid": bool (True if no errors)
            "checks": list of {"severity", "field", "message"}
            "summary": short text summary
    """
    checks = []

    # === Required fields ===
    required_fields = [
        ("invoice_number", "Invoice number"),
        ("issue_date", "Issue date"),
        ("total", "Total amount"),
    ]
    for field, label in required_fields:
        if not data.get(field):
            checks.append({
                "severity": SEVERITY_ERROR,
                "field": field,
                "message": f"{label} not found",
            })

    # === Recommended fields ===
    recommended_fields = [
        ("vendor_name", "Vendor name"),
        ("customer_name", "Customer name"),
        ("due_date", "Due date"),
        ("subtotal", "Subtotal"),
    ]
    for field, label in recommended_fields:
        if not data.get(field):
            checks.append({
                "severity": SEVERITY_WARNING,
                "field": field,
                "message": f"{label} not extracted",
            })

    # === Line items ===
    line_items = data.get("line_items") or []
    if not line_items:
        checks.append({
            "severity": SEVERITY_WARNING,
            "field": "line_items",
            "message": "No line items extracted",
        })
    else:
        # Check each line item is complete
        for idx, item in enumerate(line_items, start=1):
            missing = []
            if not item.get("description"):
                missing.append("description")
            if item.get("quantity") is None:
                missing.append("quantity")
            if item.get("line_total") is None:
                missing.append("line_total")
            if missing:
                checks.append({
                    "severity": SEVERITY_WARNING,
                    "field": f"line_items[{idx}]",
                    "message": f"Line item {idx} missing: {', '.join(missing)}",
                })

            # Check qty * unit_price = line_total
            qty = item.get("quantity")
            unit = item.get("unit_price")
            line_total = item.get("line_total")
            if qty is not None and unit is not None and line_total is not None:
                expected = round(qty * unit, 2)
                if abs(expected - line_total) > tolerance:
                    checks.append({
                        "severity": SEVERITY_WARNING,
                        "field": f"line_items[{idx}]",
                        "message": (
                            f"Line item {idx}: qty x unit_price = {expected:.2f}, "
                            f"but line_total = {line_total:.2f}"
                        ),
                    })

    # === Math checks ===
    subtotal = data.get("subtotal")
    tax = data.get("tax")
    total = data.get("total")

    # Sum of line items vs subtotal
    if subtotal is not None and line_items:
        items_sum = sum(
            (item.get("line_total") or 0) for item in line_items
        )
        items_sum = round(items_sum, 2)
        if abs(items_sum - subtotal) > tolerance:
            checks.append({
                "severity": SEVERITY_WARNING,
                "field": "subtotal",
                "message": (
                    f"Line items sum to {items_sum:.2f}, "
                    f"but subtotal = {subtotal:.2f}"
                ),
            })

    # Subtotal + tax = total
    if subtotal is not None and tax is not None and total is not None:
        expected_total = round(subtotal + tax, 2)
        if abs(expected_total - total) > tolerance:
            checks.append({
                "severity": SEVERITY_ERROR,
                "field": "total",
                "message": (
                    f"Subtotal + tax = {expected_total:.2f}, "
                    f"but total = {total:.2f}"
                ),
            })

    # === Date sanity ===
    issue_date = data.get("issue_date")
    due_date = data.get("due_date")

    if issue_date and due_date:
        try:
            iss = date_parser.parse(issue_date)
            due = date_parser.parse(due_date)
            if due < iss:
                checks.append({
                    "severity": SEVERITY_ERROR,
                    "field": "due_date",
                    "message": f"Due date ({due_date}) is before issue date ({issue_date})",
                })
            days_diff = (due - iss).days
            if days_diff > 365:
                checks.append({
                    "severity": SEVERITY_WARNING,
                    "field": "due_date",
                    "message": f"Due date is {days_diff} days after issue date (unusually long)",
                })
        except (ValueError, TypeError):
            pass

    # === Amount range sanity ===
    if total is not None:
        if total <= 0:
            checks.append({
                "severity": SEVERITY_ERROR,
                "field": "total",
                "message": f"Total is non-positive: {total}",
            })
        if total > 1_000_000:
            checks.append({
                "severity": SEVERITY_WARNING,
                "field": "total",
                "message": f"Total is unusually large: {total} (verify accuracy)",
            })

    # === Build summary ===
    error_count = sum(1 for c in checks if c["severity"] == SEVERITY_ERROR)
    warning_count = sum(1 for c in checks if c["severity"] == SEVERITY_WARNING)
    is_valid = error_count == 0

    if error_count == 0 and warning_count == 0:
        summary = "All checks passed."
    elif error_count == 0:
        summary = f"Valid with {warning_count} warning(s)."
    else:
        summary = f"INVALID: {error_count} error(s), {warning_count} warning(s)."

    return {
        "is_valid": is_valid,
        "checks": checks,
        "summary": summary,
        "error_count": error_count,
        "warning_count": warning_count,
    }