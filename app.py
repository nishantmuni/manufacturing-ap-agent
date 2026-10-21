"""
app.py: Operational AP Auditor Dashboard (Streamlit)
---------------------------------------------------
Self-guided interactive portal demonstrating enterprise multimodal 3-way matching,
split-delivery GRN aggregation, deterministic variance math, and Human-in-the-Loop
dispute staging.
"""

import os
import sqlite3
import pandas as pd
import streamlit as st
import init_db
from agent import run_deterministic_3way_match

DB_NAME = "database.sqlite"
PDF_DIR = "invoices_pdf"

st.set_page_config(
    page_title="Manufacturing AP 3-Way Matching Engine",
    page_icon="⚙️",
    layout="wide"
)

# ==============================================================================
# SECTION 1: DATABASE UTILITIES
# ==============================================================================

def load_table_data(query: str) -> pd.DataFrame:
    """Reads SQLite database tables into DataFrames for tabular review."""
    conn = sqlite3.connect(DB_NAME)
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df


# ==============================================================================
# SECTION 2: EXECUTIVE OVERVIEW & ARCHITECTURE
# ==============================================================================

st.title("🛡️ GenAI-Powered Accounts Payable 3-Way Matching Workbench")
st.markdown("### *Multimodal Invoice Auditing Across ERP Purchase Orders & Warehouse Dock Receipts*")

st.markdown("""
> **The Problem:** Enterprise AP teams lose millions to invoice leakage and manual reconciliation toil. Traditional OCR is brittle to format changes, while standard ERP rules reject minor phrasing mismatches. Conversely, unconstrained GenAI chatbots hallucinate calculations and cannot be trusted with financial disbursements.
""")

col_arch1, col_arch2, col_arch3 = st.columns(3)

with col_arch1:
    st.markdown("#### 👁️ 1. Multimodal GenAI Ingestion")
    st.caption("**Google Gemini Flash Engine**")
    st.markdown("""
    Ingests raw vendor invoice PDFs directly. Visually extracts tables, line items, and fees, then semantically reconciles vendor item descriptions to internal ERP part codes.
    """)

with col_arch2:
    st.markdown("#### ⚖️ 2. Deterministic Financial Audit")
    st.caption("**Zero-Hallucination Pricing Engine**")
    st.markdown("""
    Bypasses LLM math entirely. Python & SQL query the ERP database, aggregate split dock deliveries across all goods receipts ($\sum \text{GRNs}$), and compute line variances.
    """)

with col_arch3:
    st.markdown("#### 🛡️ 3. SOX Governance & HITL")
    st.caption("**Policy-Bound Approvals & Disputes**")
    st.markdown("""
    Enforces contract tolerances ($\le \$5.00$). Releases clean invoices automatically and stages structured dispute packages for supervisor sign-off on discrepancies.
    """)

st.markdown("---")

st.markdown("#### Select a Production Scenario to Run Audit:")

# ==============================================================================
# SECTION 3: ONE-CLICK SCENARIO CONTROLS
# ==============================================================================

col_btn1, col_btn2, col_btn3 = st.columns(3)

# Default selection initializes to Scenario 3 so the screen is never blank
if "active_pdf" not in st.session_state:
    st.session_state["active_pdf"] = "invoices_pdf/INV-9005.pdf"

with col_btn1:
    if st.button("🟢 Scenario 1: Clean Exact Match", width="stretch"):
        st.session_state["active_pdf"] = "invoices_pdf/INV-9001.pdf"

with col_btn2:
    if st.button("🟡 Scenario 2: Semantic Mapping & $2 Tolerance", width="stretch"):
        st.session_state["active_pdf"] = "invoices_pdf/INV-9002.pdf"

with col_btn3:
    if st.button("🔴 Scenario 3: Split-GRN Shortage & Dispute", width="stretch"):
        st.session_state["active_pdf"] = "invoices_pdf/INV-9005.pdf"

active_pdf = st.session_state["active_pdf"]

# Run or load audit result
if active_pdf not in st.session_state:
    st.session_state[active_pdf] = run_deterministic_3way_match(active_pdf)

res = st.session_state[active_pdf]

st.markdown("---")


# ==============================================================================
# SECTION 4: AUDIT DETERMINATION & RECONCILIATION BREAKDOWN
# ==============================================================================

st.subheader(f"1. Audit Findings: {res['invoice_id']} (Linked PO: {res['po_id']})")

status = res["status"]
if status == "Approved":
    st.success(f"**Audit Verdict: {status}** — Clean 3-way match. Invoice released for automatic payment run.")
elif status == "Warning_Approved":
    st.warning(f"**Audit Verdict: {status}** — Minor variance detected within acceptable policy threshold (<= $5.00). Approved with audit log.")
else:
    st.error(f"**Audit Verdict: {status}** — Discrepancies detected. Payment placed on administrative hold.")

st.markdown(f"**Auditor Reasoning Note:** `{res['note']}`")

# Multi-Line Reconciliation Table
if res.get("lines"):
    st.markdown("#### Itemized 3-Way Reconciliation Breakdown")
    line_data = []
    for line in res["lines"]:
        line_data.append({
            "PO Line #": line["line_number"],
            "ERP Master Code": line["item_code"],
            "Vendor Billed Description": line["billed_description"],
            "Billed Qty": line["billed_qty"],
            "Cumulative Dock Receipts (∑ GRNs)": line["received_qty"],
            "Billed Unit Price": f"${line['billed_unit_price']:.2f}",
            "Authorized PO Price": f"${line['authorized_unit_price']:.2f}",
            "Line Variance": f"${line['line_variance']:.2f}"
        })
    st.dataframe(pd.DataFrame(line_data), hide_index=True, width="stretch")

metric_c1, metric_c2 = st.columns(2)
metric_c1.metric("Unauthorized Freight Surcharge", f"${res.get('freight', 0.0):.2f}")
metric_c2.metric("Total Invoice Variance", f"${res.get('total_variance', 0.0):.2f}")

st.markdown("---")


# ==============================================================================
# SECTION 5: HUMAN-IN-THE-LOOP (HITL) GOVERNANCE WORKFLOW
# ==============================================================================

if res.get("dispute_email"):
    st.subheader("2. Human-in-the-Loop Review: Operational Dispute Workbench")
    st.caption("SOX Compliance Guardrail: High-variance invoices are staged for AP supervisor approval before vendor transmission.")

    st.text_area("Vendor Dispute Memo (Editable Draft)", value=res["dispute_email"], height=220)

    act_col1, act_col2 = st.columns(2)
    with act_col1:
        if st.button("✉️ Approve & Dispatch Dispute Notice", width="stretch"):
            st.success("Dispute notification dispatched to vendor accounts receivable.")
    with act_col2:
        if st.button("⚠️ Supervisor Manual Payment Override", width="stretch"):
            st.warning("Manager override logged. Invoice released for exception payment.")

    st.markdown("---")


# ==============================================================================
# SECTION 6: ERP GROUND TRUTH MASTER TABLES
# ==============================================================================

with st.expander("🔍 Inspect Underlying ERP & Warehouse Ground Truth Data"):
    tab_po, tab_grn, tab_inv = st.tabs(["Purchase Orders", "Warehouse Receipts (GRN)", "Invoice Ledger"])
    
    with tab_po:
        st.dataframe(
            load_table_data("SELECT po_id, line_number, item_code, ordered_qty, unit_price FROM purchase_order_lines"),
            hide_index=True,
            width="stretch"
        )
    with tab_grn:
        st.dataframe(
            load_table_data("SELECT grn_id, po_id, line_number, received_qty FROM goods_receipt_lines"),
            hide_index=True,
            width="stretch"
        )
    with tab_inv:
        st.dataframe(
            load_table_data("SELECT invoice_id, po_id, vendor, status, exception_note FROM invoices"),
            hide_index=True,
            width="stretch"
        )

#with st.sidebar:
#   st.header("Enterprise Policy Rules")
#    st.markdown("""
#    * **Tolerance Ceiling:** $\le \$5.00$ cumulative variance auto-approved.
#    * **Split Receipts:** Cumulative summation across multiple dock deliveries ($\sum \text{GRNs}$).
#    * **Short Shipments:** Automatically held from payment batch.
#    * **Unauthorized Fees:** Any non-PO freight surcharges flagged for dispute.
#    """)
#    if st.button("🔄 Reset / Re-seed Database", width="stretch"):
#        init_db.init_db()
#        st.session_state.clear()  # <-- Clear in-memory audit cache so it re-reads cleanly
#        st.success("Database restored to baseline.")
#        st.rerun()