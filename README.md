# 🛡️ Autonomous Manufacturing AP 3-Way Matching Engine

An enterprise-grade hybrid AI solution designed to automate Accounts Payable (AP) reconciliation across **vendor PDF invoices**, **ERP Purchase Orders (POs)**, and **warehouse Goods Receipt Notes (GRNs)**.

---

## 🎯 Executive Overview & Problem Statement

Manufacturing AP departments manually process thousands of complex supplier invoices monthly. Traditional approaches face severe trade-offs:
* **Legacy OCR / RPA Rules:** Brittle to layout changes; fail completely when vendor product descriptions do not match internal ERP codes word-for-word.
* **Unconstrained GenAI Prompts:** Prone to arithmetic hallucinations, rounding errors, and non-deterministic pricing math that fail SOX compliance audits.

### The Decoupled Architecture
* **Perception Layer (Google Gemini Flash):** Visually ingests raw invoice PDFs, parses multi-line tables, and semantically maps vendor phrasing (e.g., `"Heavy Duty Industrial Grade Widget Type HD"` → `WDT-HD`).
* **Deterministic Audit Engine (Python & SQL):** Bypasses LLM math entirely. Queries ground-truth ERP tables, aggregates warehouse receipts across split delivery dates (∑ GRNs), and calculates line variances.
* **Policy Governance & HITL:** Automatically approves clean orders and minor contractual tolerances (≤ $5.00), while quarantining short-shipments and drafting dispute memos for Human-in-the-Loop supervisor sign-off.

---

## 🚀 Scenarios Demonstrated

1. **Clean 3-Way Match (`INV-9001`):** Complete alignment across PO, receiving slip, and invoice. Instant auto-approval.
2. **Semantic SKU Resolution & Tolerance (`INV-9002`):** Unstructured vendor description matched to ERP item code; $2.00 variance approved under policy ceiling.
3. **Short-Shipment & Unauthorized Surcharge (`INV-9003`):** 200 units billed vs. 150 received at dock; unauthorized $150 freight fee flagged for dispute.
4. **Multi-Line Split Deliveries (`INV-9004` & `INV-9005`):** Purchase order delivered across multiple dates and partial GRNs. Accurately detects a 20-unit shortage on partial fulfillment.

---

## 💻 Local Setup & Execution

1. **Clone the repository:**
   ```bash
   git clone [https://github.com/nishantmuni/manufacturing-ap-agent.git](https://github.com/nishantmuni/manufacturing-ap-agent.git)
   cd manufacturing-ap-agent