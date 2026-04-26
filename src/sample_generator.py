"""
Generate sample invoice PDFs in different layouts for testing.
Creates 5 distinct invoice formats covering common variations.
"""

import os
import random
from datetime import datetime, timedelta
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
)
from reportlab.lib.enums import TA_RIGHT, TA_LEFT, TA_CENTER

OUTPUT_DIR = "samples"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Sample data pool
COMPANIES = [
    ("Acme Manufacturing Inc.", "1234 Industrial Way", "Boston, MA 02101"),
    ("Bluewave Logistics LLC", "789 Harbor Drive", "Miami, FL 33101"),
    ("Crystal Software Solutions", "456 Tech Park Rd", "Austin, TX 78701"),
    ("Delta Trading Co.", "321 Commerce St", "Chicago, IL 60601"),
    ("Evergreen Supply Group", "654 Oak Avenue", "Portland, OR 97201"),
]

CUSTOMERS = [
    ("Globex Corporation", "100 Business Plaza", "New York, NY 10001"),
    ("Initech Industries", "200 Office Tower", "San Francisco, CA 94101"),
    ("Jumbo Enterprises", "300 Main Street", "Seattle, WA 98101"),
    ("Kinetic Holdings", "400 Park Place", "Denver, CO 80201"),
    ("Lumiere Group", "500 Center Square", "Atlanta, GA 30301"),
]

ITEMS = [
    ("Premium widget assembly", "WID-001", 145.00),
    ("Industrial sensor module", "SEN-042", 89.50),
    ("Hydraulic actuator kit", "HYD-118", 320.00),
    ("Steel mounting bracket (set of 4)", "MNT-204", 45.75),
    ("Polymer gasket replacement", "GSK-076", 12.30),
    ("Wireless transmitter unit", "TRX-009", 215.00),
    ("Power supply (24V/10A)", "PWR-300", 178.00),
    ("Control panel assembly", "CTL-150", 425.00),
    ("Cable harness (10m)", "CBL-010", 67.50),
    ("Thermal protection housing", "THP-022", 95.00),
]


def random_invoice_data():
    """Generate randomized but consistent invoice data."""
    company = random.choice(COMPANIES)
    customer = random.choice(CUSTOMERS)
    invoice_num = f"INV-{random.randint(1000, 99999)}"
    issue_date = datetime.now() - timedelta(days=random.randint(0, 60))
    due_date = issue_date + timedelta(days=30)

    n_items = random.randint(3, 7)
    selected_items = random.sample(ITEMS, n_items)
    line_items = []
    for desc, sku, price in selected_items:
        qty = random.randint(1, 10)
        line_items.append({
            "description": desc,
            "sku": sku,
            "quantity": qty,
            "unit_price": price,
            "line_total": round(qty * price, 2),
        })

    subtotal = round(sum(i["line_total"] for i in line_items), 2)
    tax_rate = 0.085
    tax = round(subtotal * tax_rate, 2)
    total = round(subtotal + tax, 2)

    return {
        "vendor_name": company[0],
        "vendor_address": f"{company[1]}, {company[2]}",
        "customer_name": customer[0],
        "customer_address": f"{customer[1]}, {customer[2]}",
        "invoice_number": invoice_num,
        "issue_date": issue_date.strftime("%Y-%m-%d"),
        "due_date": due_date.strftime("%Y-%m-%d"),
        "line_items": line_items,
        "subtotal": subtotal,
        "tax_rate": tax_rate,
        "tax": tax,
        "total": total,
    }


def format_currency(amount):
    return f"${amount:,.2f}"


# ============================================================
# FORMAT 1: Classic professional layout
# ============================================================

def generate_format_1(filepath, data):
    doc = SimpleDocTemplate(filepath, pagesize=letter,
                            leftMargin=0.75 * inch, rightMargin=0.75 * inch,
                            topMargin=0.75 * inch, bottomMargin=0.75 * inch)
    styles = getSampleStyleSheet()
    story = []

    # Header
    title_style = ParagraphStyle("Title", parent=styles["Title"],
                                  fontSize=28, alignment=TA_RIGHT,
                                  textColor=colors.HexColor("#2C3E50"))
    story.append(Paragraph("INVOICE", title_style))
    story.append(Spacer(1, 0.2 * inch))

    # Vendor + Invoice info table
    header_data = [
        [Paragraph(f"<b>{data['vendor_name']}</b><br/>{data['vendor_address']}",
                   styles["Normal"]),
         Paragraph(
             f"<b>Invoice #:</b> {data['invoice_number']}<br/>"
             f"<b>Issue Date:</b> {data['issue_date']}<br/>"
             f"<b>Due Date:</b> {data['due_date']}",
             styles["Normal"])]
    ]
    header_table = Table(header_data, colWidths=[3.5 * inch, 3 * inch])
    header_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 0.3 * inch))

    # Bill to
    story.append(Paragraph("<b>Bill To:</b>", styles["Normal"]))
    story.append(Paragraph(
        f"{data['customer_name']}<br/>{data['customer_address']}",
        styles["Normal"]))
    story.append(Spacer(1, 0.3 * inch))

    # Line items table
    line_data = [["Description", "SKU", "Qty", "Unit Price", "Total"]]
    for item in data["line_items"]:
        line_data.append([
            item["description"],
            item["sku"],
            str(item["quantity"]),
            format_currency(item["unit_price"]),
            format_currency(item["line_total"]),
        ])

    line_table = Table(line_data,
                       colWidths=[2.8 * inch, 1 * inch, 0.6 * inch,
                                  1 * inch, 1 * inch])
    line_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2C3E50")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("ALIGN", (2, 0), (-1, -1), "RIGHT"),
        ("ALIGN", (0, 0), (1, -1), "LEFT"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
        ("TOPPADDING", (0, 0), (-1, 0), 8),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1),
         [colors.white, colors.HexColor("#F5F7FA")]),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CCCCCC")),
    ]))
    story.append(line_table)
    story.append(Spacer(1, 0.3 * inch))

    # Totals
    totals_data = [
        ["Subtotal:", format_currency(data["subtotal"])],
        [f"Tax ({data['tax_rate']*100:.1f}%):", format_currency(data["tax"])],
        ["TOTAL:", format_currency(data["total"])],
    ]
    totals_table = Table(totals_data, colWidths=[1.5 * inch, 1.5 * inch],
                          hAlign="RIGHT")
    totals_table.setStyle(TableStyle([
        ("ALIGN", (0, 0), (-1, -1), "RIGHT"),
        ("FONTNAME", (0, 2), (-1, 2), "Helvetica-Bold"),
        ("FONTSIZE", (0, 2), (-1, 2), 12),
        ("LINEABOVE", (0, 2), (-1, 2), 1, colors.black),
        ("TOPPADDING", (0, 2), (-1, 2), 6),
    ]))
    story.append(totals_table)

    doc.build(story)


# ============================================================
# FORMAT 2: Modern minimal layout
# ============================================================

def generate_format_2(filepath, data):
    doc = SimpleDocTemplate(filepath, pagesize=A4,
                            leftMargin=0.6 * inch, rightMargin=0.6 * inch,
                            topMargin=0.6 * inch, bottomMargin=0.6 * inch)
    styles = getSampleStyleSheet()
    story = []

    # Big invoice number top
    inv_style = ParagraphStyle("InvNum", parent=styles["Title"],
                                fontSize=18, textColor=colors.HexColor("#1ABC9C"),
                                alignment=TA_LEFT, spaceAfter=4)
    story.append(Paragraph(f"Invoice {data['invoice_number']}", inv_style))
    story.append(Paragraph(
        f"Issued {data['issue_date']}  ·  Due {data['due_date']}",
        styles["Normal"]))
    story.append(Spacer(1, 0.3 * inch))

    # From / To columns
    from_to_data = [[
        Paragraph(f"<b>FROM</b><br/><br/>{data['vendor_name']}<br/>"
                  f"{data['vendor_address']}", styles["Normal"]),
        Paragraph(f"<b>TO</b><br/><br/>{data['customer_name']}<br/>"
                  f"{data['customer_address']}", styles["Normal"]),
    ]]
    from_to = Table(from_to_data, colWidths=[3.4 * inch, 3.4 * inch])
    from_to.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    story.append(from_to)
    story.append(Spacer(1, 0.4 * inch))

    # Line items - cleaner style
    line_data = [["Item", "Qty", "Rate", "Amount"]]
    for item in data["line_items"]:
        line_data.append([
            f"{item['description']} ({item['sku']})",
            str(item["quantity"]),
            format_currency(item["unit_price"]),
            format_currency(item["line_total"]),
        ])

    line_table = Table(line_data,
                       colWidths=[3.6 * inch, 0.8 * inch, 1.2 * inch, 1.2 * inch])
    line_table.setStyle(TableStyle([
        ("LINEBELOW", (0, 0), (-1, 0), 1, colors.black),
        ("LINEBELOW", (0, -1), (-1, -1), 1, colors.black),
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
        ("ALIGN", (0, 0), (0, -1), "LEFT"),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(line_table)
    story.append(Spacer(1, 0.2 * inch))

    # Inline totals
    totals = [
        ["", "Subtotal", format_currency(data["subtotal"])],
        ["", f"Tax {data['tax_rate']*100:.1f}%", format_currency(data["tax"])],
        ["", "Total Due", format_currency(data["total"])],
    ]
    totals_table = Table(totals,
                         colWidths=[3.6 * inch, 2 * inch, 1.2 * inch])
    totals_table.setStyle(TableStyle([
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
        ("FONTNAME", (1, -1), (-1, -1), "Helvetica-Bold"),
        ("FONTSIZE", (1, -1), (-1, -1), 12),
        ("LINEABOVE", (1, -1), (-1, -1), 1, colors.HexColor("#1ABC9C")),
        ("TOPPADDING", (1, -1), (-1, -1), 6),
    ]))
    story.append(totals_table)

    doc.build(story)


# ============================================================
# FORMAT 3: Compact layout with notes
# ============================================================

def generate_format_3(filepath, data):
    doc = SimpleDocTemplate(filepath, pagesize=letter,
                            leftMargin=0.5 * inch, rightMargin=0.5 * inch,
                            topMargin=0.5 * inch, bottomMargin=0.5 * inch)
    styles = getSampleStyleSheet()
    story = []

    # Header bar
    header_style = ParagraphStyle("Header", parent=styles["Title"],
                                   fontSize=16, alignment=TA_CENTER,
                                   textColor=colors.white)
    header = Table([[Paragraph(
        f"INVOICE — {data['invoice_number']}", header_style)]],
        colWidths=[7.5 * inch])
    header.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#34495E")),
        ("TOPPADDING", (0, 0), (-1, -1), 12),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
    ]))
    story.append(header)
    story.append(Spacer(1, 0.2 * inch))

    # Compact info line
    story.append(Paragraph(
        f"<b>Vendor:</b> {data['vendor_name']}  |  "
        f"<b>Customer:</b> {data['customer_name']}  |  "
        f"<b>Date:</b> {data['issue_date']}  |  "
        f"<b>Due:</b> {data['due_date']}",
        styles["Normal"]))
    story.append(Spacer(1, 0.15 * inch))

    story.append(Paragraph(
        f"<i>{data['vendor_address']}</i>",
        styles["Normal"]))
    story.append(Paragraph(
        f"<i>Bill to: {data['customer_address']}</i>",
        styles["Normal"]))
    story.append(Spacer(1, 0.25 * inch))

    # Line items
    line_data = [["#", "Description", "SKU", "Qty", "Unit", "Total"]]
    for i, item in enumerate(data["line_items"], 1):
        line_data.append([
            str(i),
            item["description"],
            item["sku"],
            str(item["quantity"]),
            format_currency(item["unit_price"]),
            format_currency(item["line_total"]),
        ])

    line_table = Table(line_data,
                       colWidths=[0.4 * inch, 2.6 * inch, 0.9 * inch,
                                  0.5 * inch, 0.9 * inch, 0.9 * inch])
    line_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#ECF0F1")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ALIGN", (3, 0), (-1, -1), "RIGHT"),
        ("ALIGN", (0, 0), (0, -1), "CENTER"),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.grey),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(line_table)
    story.append(Spacer(1, 0.2 * inch))

    # Totals line
    totals_text = (
        f"Subtotal: {format_currency(data['subtotal'])}  |  "
        f"Tax ({data['tax_rate']*100:.1f}%): {format_currency(data['tax'])}  |  "
        f"<b>Total: {format_currency(data['total'])}</b>"
    )
    story.append(Paragraph(totals_text, ParagraphStyle(
        "Tot", parent=styles["Normal"], alignment=TA_RIGHT, fontSize=11)))

    # Notes section
    story.append(Spacer(1, 0.3 * inch))
    story.append(Paragraph("<b>Notes:</b>", styles["Normal"]))
    story.append(Paragraph(
        "Payment terms: Net 30. Late payments subject to 1.5% monthly fee. "
        "Please reference the invoice number when remitting payment.",
        styles["Normal"]))

    doc.build(story)


def main():
    """Generate sample invoices in different formats."""
    formats = [
        ("format_1_classic", generate_format_1),
        ("format_2_modern", generate_format_2),
        ("format_3_compact", generate_format_3),
    ]

    for name, generator in formats:
        for i in range(2):  # 2 of each format
            filepath = os.path.join(OUTPUT_DIR, f"{name}_{i+1}.pdf")
            data = random_invoice_data()
            generator(filepath, data)
            print(f"Created: {filepath}")

    print(f"\n{len(formats) * 2} sample invoices generated in {OUTPUT_DIR}/")


if __name__ == "__main__":
    random.seed(42)  # Reproducible test data
    main()