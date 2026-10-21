"""
init_db.py: Database Initialization & Seeding
---------------------------------------------
Sets up normalized relational tables in SQLite for POs, GRNs, and Invoices
with support for multi-line purchase orders and split deliveries.
"""

import os
import sqlite3

DB_NAME = "database.sqlite"

def init_db():
    if os.path.exists(DB_NAME):
        os.remove(DB_NAME)

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # 1. Purchase Order Headers & Lines
    cursor.execute("""
        CREATE TABLE purchase_orders (
            po_id TEXT PRIMARY KEY,
            vendor TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE purchase_order_lines (
            po_id TEXT,
            line_number INTEGER,
            item_code TEXT,
            ordered_qty INTEGER,
            unit_price REAL,
            PRIMARY KEY (po_id, line_number),
            FOREIGN KEY (po_id) REFERENCES purchase_orders(po_id)
        )
    """)

    # 2. Goods Receipt Headers & Lines (Warehouse Receiving Dock)
    cursor.execute("""
        CREATE TABLE goods_receipts (
            grn_id TEXT PRIMARY KEY,
            po_id TEXT,
            received_date TEXT,
            FOREIGN KEY (po_id) REFERENCES purchase_orders(po_id)
        )
    """)

    cursor.execute("""
        CREATE TABLE goods_receipt_lines (
            grn_id TEXT,
            po_id TEXT,
            line_number INTEGER,
            received_qty INTEGER,
            PRIMARY KEY (grn_id, line_number),
            FOREIGN KEY (grn_id) REFERENCES goods_receipts(grn_id)
        )
    """)

    # 3. Invoice Headers & Lines
    cursor.execute("""
        CREATE TABLE invoices (
            invoice_id TEXT PRIMARY KEY,
            po_id TEXT,
            vendor TEXT,
            freight_charges REAL DEFAULT 0.0,
            status TEXT DEFAULT 'Pending',
            exception_note TEXT,
            FOREIGN KEY (po_id) REFERENCES purchase_orders(po_id)
        )
    """)

    cursor.execute("""
        CREATE TABLE invoice_lines (
            invoice_id TEXT,
            line_number INTEGER,
            billed_item_description TEXT,
            billed_qty INTEGER,
            billed_unit_price REAL,
            PRIMARY KEY (invoice_id, line_number),
            FOREIGN KEY (invoice_id) REFERENCES invoices(invoice_id)
        )
    """)

    # ==========================================================================
    # SEED DATA: Single-Line Test Cases (Baseline Compatibility)
    # ==========================================================================
    # Scenario 1: Clean Exact Match
    cursor.execute("INSERT INTO purchase_orders VALUES ('PO-1001', 'Acme Corp')")
    cursor.execute("INSERT INTO purchase_order_lines VALUES ('PO-1001', 1, 'WDT-100', 50, 10.00)")
    cursor.execute("INSERT INTO goods_receipts VALUES ('GRN-5001', 'PO-1001', '2026-10-20')")
    cursor.execute("INSERT INTO goods_receipt_lines VALUES ('GRN-5001', 'PO-1001', 1, 50)")
    cursor.execute("INSERT INTO invoices VALUES ('INV-9001', 'PO-1001', 'Acme Corp', 0.0, 'Pending', NULL)")
    cursor.execute("INSERT INTO invoice_lines VALUES ('INV-9001', 1, 'WDT-100 Widget Standard Assembly', 50, 10.00)")

    # Scenario 2: Semantic Description Mismatch + Minor Price Variance ($0.02)
    cursor.execute("INSERT INTO purchase_orders VALUES ('PO-1002', 'Global Mfg Solutions')")
    cursor.execute("INSERT INTO purchase_order_lines VALUES ('PO-1002', 1, 'WDT-HD', 100, 25.00)")
    cursor.execute("INSERT INTO goods_receipts VALUES ('GRN-5002', 'PO-1002', '2026-10-20')")
    cursor.execute("INSERT INTO goods_receipt_lines VALUES ('GRN-5002', 'PO-1002', 1, 100)")
    cursor.execute("INSERT INTO invoices VALUES ('INV-9002', 'PO-1002', 'Global Mfg Solutions', 0.0, 'Pending', NULL)")
    cursor.execute("INSERT INTO invoice_lines VALUES ('INV-9002', 1, 'Heavy Duty Industrial Grade Widget Type HD', 100, 25.02)")

    # Scenario 3: Single-line Short Shipment (-20 units) + Unauthorized Freight ($150.00)
    cursor.execute("INSERT INTO purchase_orders VALUES ('PO-1003', 'SteelWorks Foundry Ltd.')")
    cursor.execute("INSERT INTO purchase_order_lines VALUES ('PO-1003', 1, 'ST-BAR-5M', 200, 5.00)")
    cursor.execute("INSERT INTO goods_receipts VALUES ('GRN-5003', 'PO-1003', '2026-10-21')")
    cursor.execute("INSERT INTO goods_receipt_lines VALUES ('GRN-5003', 'PO-1003', 1, 180)")
    cursor.execute("INSERT INTO invoices VALUES ('INV-9003', 'PO-1003', 'SteelWorks Foundry Ltd.', 150.0, 'Pending', NULL)")
    cursor.execute("INSERT INTO invoice_lines VALUES ('INV-9003', 1, '5-Meter Reinforced Carbon Steel Bar', 200, 5.00)")

    # ==========================================================================
    # SEED DATA: Multi-Line & Partial Split Delivery Scenario (PO-2001)
    # ==========================================================================
    # PO-2001: 3-line order to Apex Industrial Components
    cursor.execute("INSERT INTO purchase_orders VALUES ('PO-2001', 'Apex Industrial Components')")
    cursor.execute("INSERT INTO purchase_order_lines VALUES ('PO-2001', 1, 'WDT-HD', 100, 25.00)")
    cursor.execute("INSERT INTO purchase_order_lines VALUES ('PO-2001', 2, 'BOLT-HEX', 500, 0.50)")
    cursor.execute("INSERT INTO purchase_order_lines VALUES ('PO-2001', 3, 'VALVE-2IN', 50, 80.00)")

    # Split Delivery 1 (GRN-6001): 100 of Line 1, 300 of Line 2
    cursor.execute("INSERT INTO goods_receipts VALUES ('GRN-6001', 'PO-2001', '2026-10-18')")
    cursor.execute("INSERT INTO goods_receipt_lines VALUES ('GRN-6001', 'PO-2001', 1, 100)")
    cursor.execute("INSERT INTO goods_receipt_lines VALUES ('GRN-6001', 'PO-2001', 2, 300)")

    # Split Delivery 2 (GRN-6002): Remaining 200 of Line 2, and Partial 30 of Line 3
    cursor.execute("INSERT INTO goods_receipts VALUES ('GRN-6002', 'PO-2001', '2026-10-21')")
    cursor.execute("INSERT INTO goods_receipt_lines VALUES ('GRN-6002', 'PO-2001', 2, 200)")
    cursor.execute("INSERT INTO goods_receipt_lines VALUES ('GRN-6002', 'PO-2001', 3, 30)")  # 20 pending at supplier

    # Invoices for PO-2001:
    # INV-9004: Valid split billing matching GRN-6001 (Line 1: 100 units, Line 2: 300 units)
    cursor.execute("INSERT INTO invoices VALUES ('INV-9004', 'PO-2001', 'Apex Industrial Components', 0.0, 'Pending', NULL)")
    cursor.execute("INSERT INTO invoice_lines VALUES ('INV-9004', 1, 'Heavy Duty Widget Type HD', 100, 25.00)")
    cursor.execute("INSERT INTO invoice_lines VALUES ('INV-9004', 2, 'Grade 8 Hex Bolts', 300, 0.50)")

    # INV-9005: Premature overbilled split invoice (Bills all 50 units of Line 3, but dock received only 30 units)
    cursor.execute("INSERT INTO invoices VALUES ('INV-9005', 'PO-2001', 'Apex Industrial Components', 0.0, 'Pending', NULL)")
    cursor.execute("INSERT INTO invoice_lines VALUES ('INV-9005', 1, '2-Inch Industrial Flow Valve', 50, 80.00)")

    conn.commit()
    conn.close()
    print(f"Database '{DB_NAME}' initialized with multi-line PO & split-GRN support.")

if __name__ == "__main__":
    init_db()