"""
Pattern matchers for extracting specific fields from invoice text.
Each parser function takes raw text and returns either the extracted value
or None if the pattern wasn't found.

Designed defensively - returns None on missing data rather than crashing,
so the validation layer can flag what's missing.
"""

import re
from datetime import datetime
from dateutil import parser as date_parser


def parse_invoice_number(text):
    """Find invoice number using common patterns."""
    patterns = [
        r"Invoice\s*#?\s*[:\-]?\s*(INV[-\s]?\d+)",
        r"Invoice\s*Number\s*[:\-]?\s*(INV[-\s]?\d+)",
        r"Invoice\s+(INV[-\s]?\d+)",
        r"\b(INV[-\s]?\d{3,})\b",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            num = match.group(1).upper().replace(" ", "-")
            if num.startswith("INV") and "-" not in num:
                num = f"INV-{num[3:]}"
            return num
    return None


def parse_dates(text):
    """Find issue date and due date. Returns (issue_date, due_date) ISO strings."""
    issue_date = None
    due_date = None

    issue_patterns = [
        r"Issue\s*Date\s*[:\-]?\s*([\d\-/]+)",
        r"Issued\s+(\d{4}-\d{2}-\d{2})",
        r"Issued\s*[:\-]?\s*([\d\-/]+)",
        r"Date\s*[:\-]?\s*([\d\-/]+)",
        r"Issued\s+([A-Z][a-z]+\s+\d{1,2},?\s+\d{4})",
    ]
    due_patterns = [
        r"Due\s*Date\s*[:\-]?\s*([\d\-/]+)",
        r"Due\s+(\d{4}-\d{2}-\d{2})",
        r"Due\s*[:\-]?\s*([\d\-/]+)",
        r"Due\s+([A-Z][a-z]+\s+\d{1,2},?\s+\d{4})",
    ]

    for pattern in issue_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            issue_date = _normalize_date(match.group(1))
            if issue_date:
                break

    for pattern in due_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            due_date = _normalize_date(match.group(1))
            if due_date:
                break

    return issue_date, due_date


def _normalize_date(date_string):
    """Convert any date format to ISO YYYY-MM-DD."""
    try:
        cleaned = date_string.strip().rstrip(".,")
        parsed = date_parser.parse(cleaned, fuzzy=False)
        return parsed.strftime("%Y-%m-%d")
    except (ValueError, TypeError, OverflowError):
        return None


def parse_currency_amount(text):
    """Extract a numeric amount from a string with currency symbols."""
    if not text:
        return None
    cleaned = re.sub(r"[^\d.\-]", "", text)
    if not cleaned or cleaned in ("-", "."):
        return None
    try:
        return round(float(cleaned), 2)
    except ValueError:
        return None


def parse_totals(text):
    """Find subtotal, tax, and total amounts."""
    result = {"subtotal": None, "tax": None, "total": None}

    subtotal_patterns = [
        r"Subtotal\s*[:\-]?\s*\$?([\d,]+\.\d{2})",
        r"Sub-?total\s*[:\-]?\s*\$?([\d,]+\.\d{2})",
    ]
    for pattern in subtotal_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            result["subtotal"] = parse_currency_amount(match.group(1))
            break

    tax_patterns = [
        r"Tax\s*\([\d.]+%?\)\s*[:\-]?\s*\$?([\d,]+\.\d{2})",
        r"Tax\s+[\d.]+%?\s*[:\-]?\s*\$?([\d,]+\.\d{2})",
        r"Tax\s*[:\-]?\s*\$?([\d,]+\.\d{2})",
        r"Sales\s*Tax\s*[:\-]?\s*\$?([\d,]+\.\d{2})",
    ]
    for pattern in tax_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            result["tax"] = parse_currency_amount(match.group(1))
            break

    total_patterns = [
        r"(?<!Sub)(?<!Sub-)Total\s*Due\s*[:\-]?\s*\$?([\d,]+\.\d{2})",
        r"(?<!Sub)(?<!Sub-)TOTAL\s*[:\-]?\s*\$?([\d,]+\.\d{2})",
        r"(?<!Sub)(?<!Sub-)\bTotal\s*[:\-]?\s*\$?([\d,]+\.\d{2})",
        r"Amount\s*Due\s*[:\-]?\s*\$?([\d,]+\.\d{2})",
        r"Grand\s*Total\s*[:\-]?\s*\$?([\d,]+\.\d{2})",
    ]
    for pattern in total_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            result["total"] = parse_currency_amount(match.group(1))
            break

    return result


# ============================================================
# IMPROVED PARTY DETECTION
# ============================================================

# Words that should never appear in a vendor or customer name
NAME_BLACKLIST = {
    "invoice", "issued", "due", "date", "bill", "from", "to",
    "vendor", "customer", "tax", "total", "subtotal", "amount",
    "payment", "terms", "notes", "remit",
}


def _is_likely_name(line):
    """Check if a line looks like a company name."""
    if not line or len(line) < 3 or len(line) > 80:
        return False
    line_lower = line.lower()

    # Reject lines containing date patterns
    if re.search(r"\d{4}-\d{2}-\d{2}", line):
        return False
    # Reject lines with currency
    if "$" in line:
        return False
    # Reject lines starting with digits (likely an address number)
    if line[0].isdigit():
        return False
    # Reject lines with too many digits (likely metadata)
    if sum(c.isdigit() for c in line) > 4:
        return False
    # Reject lines starting with blacklisted keywords
    first_word = line_lower.split()[0] if line_lower.split() else ""
    if first_word in NAME_BLACKLIST:
        return False
    # Should start with a capital letter
    if not line[0].isupper():
        return False
    return True


def _clean_name(name):
    """Strip metadata that bled into a captured name."""
    if not name:
        return None
    # Remove trailing pipes and after
    name = re.sub(r"\s*\|.*$", "", name).strip()
    # Remove "Invoice #..." that bled in
    name = re.sub(r"\s*Invoice\s*#?.*$", "", name, flags=re.IGNORECASE).strip()
    # Remove "INV-..." that bled in
    name = re.sub(r"\s*INV[-\s]?\d+.*$", "", name).strip()
    # Remove date strings
    name = re.sub(r"\s*\d{4}-\d{2}-\d{2}.*$", "", name).strip()
    return name if name else None


def parse_parties(text):
    """
    Extract vendor (sender) and customer (recipient) names.
    Returns (vendor_name, customer_name).

    Handles three layout patterns:
    1. Stacked: "Bill To:\n<customer>" (Format 1)
    2. Two-column: "FROM <vendor>  TO  <customer>" on same line (Format 2)
    3. Inline: "Vendor: <name>" (Format 3 compact)
    """
    vendor_name = None
    customer_name = None

    # === LAYOUT 2 FIRST: Two-column FROM/TO (Format 2 modern) ===
    # In some PDFs, "FROM" and "TO" are visual columns but render as one text line.
    # We try to detect and split this case before falling through to other layouts.
    # Format 2 pattern: "FROM TO" header on one line, both names on the next line
    # Or stacked: "FROM\n<vendor>\nTO\n<customer>"
    column_match = re.search(
        r"FROM\s+TO\s*\n\s*([A-Z][^\n]{2,150})\s*\n",
        text,
    )
    # Stacked variant where FROM is on its own line (separate from TO)
    stacked_from_match = None
    stacked_to_match = None
    if not column_match:
        stacked_from_match = re.search(
            r"^\s*FROM\s*\n\s*([A-Z][^\n]{2,80})\s*\n",
            text,
            re.MULTILINE,
        )
        stacked_to_match = re.search(
            r"^\s*TO\s*\n\s*([A-Z][^\n]{2,80})\s*\n",
            text,
            re.MULTILINE,
        )
    to_match = stacked_to_match  # for the existing if-check below

    if column_match and not to_match:
        # FROM line might contain BOTH names (rendered side-by-side)
        merged_line = column_match.group(1).strip()
        # Try to split on 2+ spaces first
        parts = re.split(r"\s{2,}", merged_line)
        if len(parts) >= 2:
            v_candidate = _clean_name(parts[0].strip())
            c_candidate = _clean_name(parts[1].strip())
            if _is_likely_name(v_candidate):
                vendor_name = v_candidate
            if _is_likely_name(c_candidate):
                customer_name = c_candidate
        else:
            # Single space gap - try to split on transition between two
            # company names (a lowercase letter or "." or "Inc/LLC/Co/Corp"
            # followed by a capitalized word, possibly across a space)
            split_attempt = _split_two_company_names(merged_line)
            if split_attempt:
                v_candidate, c_candidate = split_attempt
                if _is_likely_name(v_candidate):
                    vendor_name = v_candidate
                if _is_likely_name(c_candidate):
                    customer_name = c_candidate
            else:
                # Couldn't split - treat as single vendor name
                v_candidate = _clean_name(merged_line)
                if _is_likely_name(v_candidate):
                    vendor_name = v_candidate

    # Stacked FROM/TO on separate lines (vendor and customer fully separated)
    elif stacked_from_match:
        v_candidate = _clean_name(stacked_from_match.group(1).strip())
        if _is_likely_name(v_candidate):
            vendor_name = v_candidate
        if stacked_to_match:
            c_candidate = _clean_name(stacked_to_match.group(1).strip())
            if _is_likely_name(c_candidate):
                customer_name = c_candidate

    # If we found both via Layout 2, return early
    if vendor_name and customer_name:
        return vendor_name, customer_name

    # === LAYOUT 1: Stacked - look for Bill To label ===
    if not customer_name:
        customer_patterns_multiline = [
            r"Bill\s*To\s*:?\s*\n\s*([^\n]+)",
            r"^\s*TO\s*\n+\s*([^\n]+)",
            r"Customer\s*:?\s*\n\s*([^\n]+)",
        ]
        for pattern in customer_patterns_multiline:
            match = re.search(pattern, text, re.MULTILINE | re.IGNORECASE)
            if match:
                candidate = _clean_name(match.group(1).strip())
                if _is_likely_name(candidate):
                    customer_name = candidate
                    break

    # === LAYOUT 3: Inline customer ===
    if not customer_name:
        inline_patterns = [
            r"Bill\s*to\s*:\s*([A-Z][^\n,|]+?)(?=\s*[\n|,]|$)",
            r"Customer\s*:\s*([A-Z][^\n,|]+?)(?=\s*[\n|,]|$)",
        ]
        for pattern in inline_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                candidate = _clean_name(match.group(1).strip())
                if _is_likely_name(candidate):
                    customer_name = candidate
                    break

    # === Vendor detection (if not already found) ===
    if not vendor_name:
        vendor_patterns_labeled = [
            r"^\s*FROM\s*\n+\s*([^\n]+)",
            r"From\s*:?\s*\n\s*([^\n]+)",
            r"Vendor\s*:\s*([A-Z][^\n,|]+?)(?=\s*[\n|,]|$)",
        ]
        for pattern in vendor_patterns_labeled:
            match = re.search(pattern, text, re.MULTILINE | re.IGNORECASE)
            if match:
                captured = match.group(1).strip()
                # Try splitting on 2+ spaces in case of column layout
                parts = re.split(r"\s{2,}", captured)
                candidate = _clean_name(parts[0].strip())
                if _is_likely_name(candidate):
                    vendor_name = candidate
                    if len(parts) >= 2 and not customer_name:
                        cust = _clean_name(parts[1].strip())
                        if _is_likely_name(cust):
                            customer_name = cust
                    break

    # === Fallback: scan first lines for first valid company name ===
    if not vendor_name:
        lines = [l.strip() for l in text.split("\n") if l.strip()]
        for line in lines[:15]:
            cleaned = _clean_name(line)
            if cleaned and _is_likely_name(cleaned):
                if customer_name and cleaned == customer_name:
                    continue
                vendor_name = cleaned
                break

    return vendor_name, customer_name


# Common company name terminators - words that typically end a company name
COMPANY_SUFFIXES = [
    "Inc", "Inc.", "LLC", "LLC.", "Ltd", "Ltd.", "Limited",
    "Corp", "Corp.", "Corporation", "Co", "Co.", "Company",
    "Group", "Holdings", "Industries", "Enterprises", "Partners",
    "Solutions", "Logistics", "Manufacturing", "Trading",
    "Supply", "Software", "Services", "Systems", "Technologies",
    "Tech", "Networks", "Consulting",
]


def _split_two_company_names(line):
    """
    Try to split a line that contains two company names back-to-back.

    Strategy: find a known company suffix (Inc, LLC, Co., Group, etc.)
    followed by a space and a capitalized word - that's the boundary.

    Returns (vendor_name, customer_name) tuple, or None if can't split.

    Examples:
        "Acme Manufacturing Inc. Globex Corporation"
            -> ("Acme Manufacturing Inc.", "Globex Corporation")
        "Evergreen Supply Group Jumbo Enterprises"
            -> ("Evergreen Supply Group", "Jumbo Enterprises")
    """
    # Build pattern: any suffix word, then whitespace, then capital letter
    suffix_pattern = "|".join(re.escape(s) for s in COMPANY_SUFFIXES)
    pattern = rf"\b({suffix_pattern})\b\s+([A-Z])"

    match = re.search(pattern, line)
    if not match:
        return None

    split_pos = match.end(1)  # End of the matched suffix
    vendor = line[:split_pos].strip()
    customer = line[split_pos:].strip()

    if vendor and customer:
        return vendor, customer
    return None

# ============================================================
# IMPROVED LINE ITEM EXTRACTION (with text fallback)
# ============================================================

def parse_line_items_from_table(table_rows):
    """Parse line items from a structured table."""
    if not table_rows or len(table_rows) < 2:
        return []

    header_row = None
    header_idx = 0
    for i, row in enumerate(table_rows[:5]):
        row_text = " ".join(str(c).lower() for c in row if c)
        if any(
            keyword in row_text
            for keyword in ["description", "item", "qty", "quantity", "amount", "total", "rate", "price"]
        ):
            header_row = row
            header_idx = i
            break

    if not header_row:
        return []

    col_map = {}
    for i, cell in enumerate(header_row):
        if not cell:
            continue
        cell_lower = str(cell).lower().strip()
        if "desc" in cell_lower or "item" in cell_lower:
            col_map["description"] = i
        elif "sku" in cell_lower or "code" in cell_lower:
            col_map["sku"] = i
        elif "qty" in cell_lower or "quantity" in cell_lower:
            col_map["quantity"] = i
        elif "unit" in cell_lower or "rate" in cell_lower or "price" in cell_lower:
            col_map["unit_price"] = i
        elif "total" in cell_lower or "amount" in cell_lower:
            col_map["line_total"] = i

    if "description" not in col_map:
        return []

    line_items = []
    for row in table_rows[header_idx + 1 :]:
        if not row or all(not c for c in row):
            continue

        first_cell = str(row[0] if row else "").lower()
        if any(kw in first_cell for kw in ["subtotal", "tax", "total", "amount due"]):
            continue

        item = {
            "description": None,
            "sku": None,
            "quantity": None,
            "unit_price": None,
            "line_total": None,
        }

        if "description" in col_map and col_map["description"] < len(row):
            desc = row[col_map["description"]]
            item["description"] = str(desc).strip() if desc else None

        if "sku" in col_map and col_map["sku"] < len(row):
            sku = row[col_map["sku"]]
            item["sku"] = str(sku).strip() if sku else None

        if "quantity" in col_map and col_map["quantity"] < len(row):
            qty_text = str(row[col_map["quantity"]]).strip()
            try:
                item["quantity"] = int(qty_text)
            except (ValueError, TypeError):
                pass

        if "unit_price" in col_map and col_map["unit_price"] < len(row):
            item["unit_price"] = parse_currency_amount(str(row[col_map["unit_price"]]))

        if "line_total" in col_map and col_map["line_total"] < len(row):
            item["line_total"] = parse_currency_amount(str(row[col_map["line_total"]]))

        # Description merged with SKU like "Premium widget (WID-001)"
        if item["description"] and not item["sku"]:
            sku_match = re.search(r"\(([\w-]+)\)\s*$", item["description"])
            if sku_match:
                item["sku"] = sku_match.group(1)
                item["description"] = re.sub(r"\s*\([\w-]+\)\s*$", "", item["description"]).strip()

        if item["description"] and (item["quantity"] or item["line_total"]):
            line_items.append(item)

    return line_items


def parse_line_items_from_text(text):
    """
    Fallback: extract line items from raw text when no table is detected.
    Uses pattern matching to find rows with description, SKU, qty, prices.

    Looks for lines like:
        Premium widget (WID-001) 5 $145.00 $725.00
        Industrial sensor (SEN-042) 3 $89.50 $268.50
    """
    items = []

    # Pattern: text + (SKU) + quantity + $price + $total
    pattern = re.compile(
        r"^(.+?)\s*\(([A-Z]+-\d+)\)\s+(\d+)\s+\$?([\d,]+\.\d{2})\s+\$?([\d,]+\.\d{2})\s*$",
        re.MULTILINE,
    )

    for match in pattern.finditer(text):
        description = match.group(1).strip()
        sku = match.group(2).strip()
        try:
            quantity = int(match.group(3))
        except ValueError:
            continue
        unit_price = parse_currency_amount(match.group(4))
        line_total = parse_currency_amount(match.group(5))

        # Skip lines that are obviously not line items
        if any(kw in description.lower() for kw in ["subtotal", "tax", "total", "due"]):
            continue

        items.append({
            "description": description,
            "sku": sku,
            "quantity": quantity,
            "unit_price": unit_price,
            "line_total": line_total,
        })

    return items