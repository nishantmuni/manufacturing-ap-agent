"""
tools.py: ERP Integration & Multi-Line Tooling Layer
---------------------------------------------------
Provides normalized PO and GRN query utilities, aggregates dock receipts
across multiple deliveries, and manages database updates.
"""

import sqlite3
from typing import Dict, Any, List

DB_NAME = "database.sqlite"

def get_db_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def get_po_details(po_id: str) -> Dict[str, Any]:
    """Fetches PO header and all associated line items."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM purchase_orders WHERE po_id = ?", (po_id,))
    po_header = cursor.fetchone()

    if not po_header:
        conn.close()
        return {"error": f"Purchase Order {po_id} not found."}

    cursor.execute("SELECT * FROM purchase_order_lines WHERE po_id = ? ORDER BY line_number", (po_id,))
    lines = [dict(row) for row in cursor.fetchall()]
    conn.close()

    return {
        "po_id": po_header["po_id"],
        "vendor": po_header["vendor"],
        "lines": lines
    }

def get_aggregate_receipts_for_po_lines(po_id: str) -> Dict[int, int]:
    """
    Calculates total accepted quantities at the dock across ALL Goods Receipt Notes (GRNs)
    for each line number of a Purchase Order.
    
    Returns:
        Dict[int, int]: Mapping of {line_number: total_received_quantity}
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT line_number, SUM(received_qty) as total_received
        FROM goods_receipt_lines
        WHERE po_id = ?
        GROUP BY line_number
    """, (po_id,))
    
    receipt_map = {row["line_number"]: row["total_received"] for row in cursor.fetchall()}
    conn.close()
    return receipt_map

def update_invoice_status(invoice_id: str, status: str, exception_note: str = "") -> Dict[str, str]:
    """Updates ERP invoice status and audit log."""
    print(f"  [Tool: Write-Back] Updating {invoice_id} -> Status: '{status}'")
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE invoices SET status = ?, exception_note = ? WHERE invoice_id = ?",
        (status, exception_note, invoice_id)
    )
    conn.commit()
    conn.close()
    return {"status": "success", "invoice_id": invoice_id, "updated_status": status}

def draft_dispute_email(vendor_name: str, invoice_id: str, po_id: str, dispute_reason: str) -> str:
    """Formats a professional AP vendor dispute notice for HITL review."""
    print(f"  [Tool: Dispute Drafter] Staging vendor dispute memo for -> {vendor_name}")
    return f"""Subject: Discrepancy Notice: Invoice {invoice_id} / Purchase Order {po_id}

Dear Accounts Receivable Team at {vendor_name},

During our automated 3-way matching audit for invoice {invoice_id} against Purchase Order {po_id}, our AP system identified the following discrepancies:

Discrepancy Details:
{dispute_reason}

Payment for this invoice is currently on administrative hold pending credit memo adjustment or proof of delivery. Please review and provide an amended invoice.

Best regards,
Operational Finance & AP Audit Team
Plant 4 Manufacturing Facility
"""