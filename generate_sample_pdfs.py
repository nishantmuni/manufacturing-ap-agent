"""
generate_sample_pdfs.py: Mock Vendor PDF Invoice Generator
---------------------------------------------------------
Generates sample vendor PDF invoices including single-line baseline tests
and multi-line partial delivery split-invoicing scenarios.
"""

import os
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

PDF_DIR = "invoices_pdf"

def create_invoice_pdf(filename, vendor_info, invoice_meta, line_items, total_info):
    os.makedirs(PDF_DIR, exist_ok=True)
    filepath = os.path.join(PDF_DIR, filename)
    doc = SimpleDocTemplate(filepath, pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontSize=18,
        leading=22,
        textColor=colors.HexColor("#1A365D")
    )
    bold_style = ParagraphStyle(
        'BoldMeta',
        parent=styles['Normal'],
        fontSize=10,
        leading=14,
        fontName="Helvetica-Bold"
    )
    normal_style = ParagraphStyle(
        'RegularMeta',
        parent=styles['Normal'],
        fontSize=10,
        leading=14
    )
    
    elements = []
    
    # Header: Vendor Name & Document Metadata
    header_data = [
        [Paragraph(vendor_info["name"], title_style), Paragraph("<b>COMMERCIAL INVOICE</b>", title_style)],
        [
            Paragraph(vendor_info["address"], normal_style),
            Paragraph(f"<b>Invoice #:</b> {invoice_meta['invoice_id']}<br/><b>Date:</b> {invoice_meta['date']}<br/><b>PO Reference:</b> {invoice_meta['po_id']}", normal_style)
        ]
    ]
    header_table = Table(header_data, colWidths=[320, 220])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 10),
    ]))
    elements.append(header_table)
    elements.append(Spacer(1, 15))
    
    # Bill To Box
    bill_to_data = [
        [Paragraph("<b>BILL TO:</b>", bold_style)],
        [Paragraph("Industrial Manufacturing Corp.<br/>Plant 4 AP Operations<br/>Chicago, IL, USA", normal_style)]
    ]
    bill_to_table = Table(bill_to_data, colWidths=[540])
    bill_to_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#F7FAFC")),
        ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor("#E2E8F0")),
        ('PADDING', (0,0), (-1,-1), 8),
    ]))
    elements.append(bill_to_table)
    elements.append(Spacer(1, 15))
    
    # Line Items Table
    table_rows = [["Line", "Item Description", "Qty", "Unit Price", "Total"]]
    for idx, item in enumerate(line_items, 1):
        table_rows.append([
            str(idx),
            item["description"],
            str(item["qty"]),
            f"${item['unit_price']:.2f}",
            f"${item['qty'] * item['unit_price']:.2f}"
        ])
    
    # Freight Row if present
    if total_info.get("freight", 0) > 0:
        table_rows.append([
            "",
            total_info.get("freight_label", "Freight / Handling Surcharge"),
            "1",
            f"${total_info['freight']:.2f}",
            f"${total_info['freight']:.2f}"
        ])
        
    table_rows.append(["", "", "", "GRAND TOTAL:", f"${total_info['grand_total']:.2f}"])
    
    item_table = Table(table_rows, colWidths=[35, 275, 50, 90, 90])
    item_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#2B6CB0")),
        ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('GRID', (0,0), (-1,-2), 0.5, colors.HexColor("#CBD5E0")),
        ('FONTNAME', (3,-1), (-1,-1), 'Helvetica-Bold'),
        ('LINEABOVE', (3,-1), (-1,-1), 1.5, colors.HexColor("#1A365D")),
        ('ALIGN', (2,0), (-1,-1), 'RIGHT'),
    ]))
    elements.append(item_table)
    
    elements.append(Spacer(1, 20))
    elements.append(Paragraph("<b>Payment Terms:</b> Net 30. Remit payment to accounts receivable.", normal_style))
    
    doc.build(elements)
    print(f"Generated PDF: {filepath}")

def generate_all_invoices():
    # Baseline Scenario 1: Clean Exact Match
    create_invoice_pdf(
        filename="INV-9001.pdf",
        vendor_info={"name": "Acme Corp", "address": "123 Industrial Parkway, Sector 4<br/>support@acmecorp.com"},
        invoice_meta={"invoice_id": "INV-9001", "po_id": "PO-1001", "date": "2026-10-21"},
        line_items=[{"description": "WDT-100 Widget Standard Assembly", "qty": 50, "unit_price": 10.00}],
        total_info={"freight": 0.0, "grand_total": 500.00}
    )

    # Baseline Scenario 2: Semantic Mismatch + $0.02 Unit Delta
    create_invoice_pdf(
        filename="INV-9002.pdf",
        vendor_info={"name": "Global Mfg Solutions", "address": "88 Fabrik Lane, Industrial Zone<br/>billing@globalmfg.com"},
        invoice_meta={"invoice_id": "INV-9002", "po_id": "PO-1002", "date": "2026-10-21"},
        line_items=[{"description": "Heavy Duty Industrial Grade Widget Type HD", "qty": 100, "unit_price": 25.02}],
        total_info={"freight": 0.0, "grand_total": 2502.00}
    )

    # Baseline Scenario 3: Single-line Short Shipment + Unauthorized Freight
    create_invoice_pdf(
        filename="INV-9003.pdf",
        vendor_info={"name": "SteelWorks Foundry Ltd.", "address": "400 Smelting Way, Harbor District<br/>ar@steelworks.com"},
        invoice_meta={"invoice_id": "INV-9003", "po_id": "PO-1003", "date": "2026-10-21"},
        line_items=[{"description": "5-Meter Reinforced Carbon Steel Bar", "qty": 200, "unit_price": 5.00}],
        total_info={"freight": 150.00, "freight_label": "Expedited Priority Freight Fee", "grand_total": 1150.00}
    )

    # Multi-Line Scenario A (INV-9004): Valid Partial Split Billing against PO-2001
    create_invoice_pdf(
        filename="INV-9004.pdf",
        vendor_info={"name": "Apex Industrial Components", "address": "1000 Assembly Drive, Precision Park<br/>ap@apexindustrial.com"},
        invoice_meta={"invoice_id": "INV-9004", "po_id": "PO-2001", "date": "2026-10-21"},
        line_items=[
            {"description": "Heavy Duty Widget Type HD", "qty": 100, "unit_price": 25.00},
            {"description": "Grade 8 Hex Bolts (Box of 1)", "qty": 300, "unit_price": 0.50}
        ],
        total_info={"freight": 0.0, "grand_total": 2650.00}
    )

    # Multi-Line Scenario B (INV-9005): Overbilled Split Billing against PO-2001
    create_invoice_pdf(
        filename="INV-9005.pdf",
        vendor_info={"name": "Apex Industrial Components", "address": "1000 Assembly Drive, Precision Park<br/>ap@apexindustrial.com"},
        invoice_meta={"invoice_id": "INV-9005", "po_id": "PO-2001", "date": "2026-10-21"},
        line_items=[
            {"description": "2-Inch Industrial Flow Valve", "qty": 50, "unit_price": 80.00}
        ],
        total_info={"freight": 0.0, "grand_total": 4000.00}
    )

if __name__ == "__main__":
    generate_all_invoices()