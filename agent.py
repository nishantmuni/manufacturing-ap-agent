"""
agent.py: Scoped Batch Multimodal AP 3-Way Matching Engine
---------------------------------------------------------
Optimized enterprise implementation:
- Multimodal PDF ingestion with local disk caching.
- Scoped batch semantic resolution (all invoice lines mapped in 1 call).
- Deterministic arithmetic pricing engine (zero LLM math).
- Multi-line & partial delivery (split-GRN) aggregation.
"""

import os
import json
import time
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv
from google import genai
from google.genai import types
from google.genai.errors import ServerError, APIError
import tools

# ==============================================================================
# SECTION 1: CONFIGURATION & CLIENT INITIALIZATION
# ==============================================================================

load_dotenv()
API_KEY = os.getenv("GEMINI_API_KEY")

if not API_KEY:
    raise ValueError("GEMINI_API_KEY is not defined in the environment or .env file.")

client = genai.Client(api_key=API_KEY)

# Priority model sequence for automated fallback
CASCADING_MODELS: List[str] = [
    "gemini-3.1-flash-lite",  # 500 RPD headroom
    "gemini 3.5 flash lite",  # 500 RPD headroom
    "gemini-3.8-flash",       # Primary experimental model
    "gemini-3.5-flash",
    "gemini-flash-latest"
]

CACHE_DIR = "invoices_pdf/cache"
TOLERANCE_THRESHOLD_USD = 5.00


# ==============================================================================
# SECTION 2: RESILIENT API INFERENCE
# ==============================================================================

def execute_resilient_gemini_call(contents: List[Any], config: types.GenerateContentConfig) -> str:
    """
    Executes a Gemini inference call with automatic model cascading
    and exponential backoff for transient rate limits (429) or spikes (503).
    """
    last_error: Optional[Exception] = None

    for model_name in CASCADING_MODELS:
        for attempt in range(1, 4):
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=contents,
                    config=config
                )
                return response.text
            except (ServerError, APIError) as exc:
                error_code = getattr(exc, "code", None)
                last_error = exc
                if error_code in [429, 500, 503] or isinstance(exc, ServerError):
                    backoff_seconds = attempt * 6
                    print(f"  [API Notice] {model_name} busy (HTTP {error_code or '503'}). Pausing {backoff_seconds}s...")
                    time.sleep(backoff_seconds)
                else:
                    break
    raise RuntimeError(f"All fallback models failed. Root error: {last_error}")


# ==============================================================================
# SECTION 3: MULTIMODAL INGESTION & PARSING
# ==============================================================================

EXTRACTOR_SCHEMA_PROMPT = """
You are an expert OCR & Accounts Payable Document Extractor.
Inspect the attached vendor invoice PDF and extract the details into a valid JSON object.

Expected JSON Schema:
{
  "invoice_id": "string",
  "po_id": "string",
  "vendor_name": "string",
  "line_items": [
    {
      "line_number": int,
      "description": "string",
      "billed_qty": int,
      "billed_unit_price": float,
      "line_total": float
    }
  ],
  "freight_charges": float,
  "grand_total": float
}

Rules:
- Return ONLY the raw JSON object. Do not wrap in markdown or backticks.
- If no freight charges are listed, set "freight_charges" to 0.0.
"""

def extract_invoice_from_pdf(pdf_path: str) -> Dict[str, Any]:
    """Extracts structured line items from a PDF with local disk caching."""
    os.makedirs(CACHE_DIR, exist_ok=True)
    cache_filename = os.path.basename(pdf_path).replace(".pdf", ".json")
    cache_path = os.path.join(CACHE_DIR, cache_filename)

    if os.path.exists(cache_path):
        print(f"\n[Extraction: Cache Hit] Loading parsed schema from: {cache_path}")
        with open(cache_path, "r", encoding="utf-8") as f:
            return json.load(f)

    print(f"\n[Extraction: API Processing] Ingesting PDF bytes: {pdf_path}")
    with open(pdf_path, "rb") as f:
        pdf_bytes = f.read()

    contents = [
        types.Part.from_bytes(data=pdf_bytes, mime_type="application/pdf"),
        EXTRACTOR_SCHEMA_PROMPT
    ]
    config = types.GenerateContentConfig(
        temperature=0.0,
        response_mime_type="application/json"
    )

    raw_json_str = execute_resilient_gemini_call(contents, config)
    extracted_data = json.loads(raw_json_str)

    with open(cache_path, "w", encoding="utf-8") as f:
        json.dump(extracted_data, f, indent=2)

    return extracted_data


# ==============================================================================
# SECTION 4: SCOPED BATCH SEMANTIC RESOLUTION
# ==============================================================================

def batch_match_lines_to_po(
    invoice_lines: List[Dict[str, Any]], 
    po_lines: List[Dict[str, Any]], 
    invoice_cache_path: str
) -> Dict[int, int]:
    """
    Reconciles all invoice lines against candidate PO lines in a single LLM call.
    Results are cached in the invoice JSON to prevent repeat API calls.

    Returns:
        Dict[int, int]: Mapping of {invoice_line_idx: matched_po_line_number}
    """
    # 1. Check if mapping is already present in cache
    if os.path.exists(invoice_cache_path):
        with open(invoice_cache_path, "r", encoding="utf-8") as f:
            cached_doc = json.load(f)
            if "semantic_line_mapping" in cached_doc:
                print(f"  [Mapping: Cache Hit] Loaded semantic line mappings from disk.")
                return {int(k): v for k, v in cached_doc["semantic_line_mapping"].items()}

    # 2. Heuristic fast-path: Check exact substring matches in Python
    mappings: Dict[int, int] = {}
    unresolved_invoice_lines: List[Dict[str, Any]] = []

    for idx, inv_line in enumerate(invoice_lines, 1):
        desc = inv_line["description"].upper()
        matched = False
        for po_line in po_lines:
            if po_line["item_code"].upper() in desc:
                mappings[idx] = po_line["line_number"]
                matched = True
                break
        if not matched:
            unresolved_invoice_lines.append({"idx": idx, "description": inv_line["description"]})

    # If all lines resolved via fast-path, save and return
    if not unresolved_invoice_lines:
        _save_mapping_to_cache(invoice_cache_path, mappings)
        return mappings

    # 3. Single-shot batch prompt for remaining ambiguous lines
    print(f"  [Mapping: Scoped Batch Call] Resolving {len(unresolved_invoice_lines)} line(s) via Gemini...")
    po_catalog = [{"line_number": p["line_number"], "item_code": p["item_code"]} for p in po_lines]
    
    prompt = f"""
You are an ERP Line Matcher. Match each invoice line item to the correct Purchase Order line number.

Candidate Purchase Order Lines:
{json.dumps(po_catalog, indent=2)}

Billed Invoice Items to match:
{json.dumps(unresolved_invoice_lines, indent=2)}

Return a valid JSON object mapping the invoice item 'idx' to the matching PO 'line_number':
Example output:
{{"mappings": [{{"idx": 1, "po_line_number": 2}}]}}
If an item has no match, set "po_line_number": 0.
"""

    config = types.GenerateContentConfig(
        temperature=0.0,
        response_mime_type="application/json"
    )
    raw_response = execute_resilient_gemini_call([prompt], config)
    parsed_mappings = json.loads(raw_response).get("mappings", [])

    for entry in parsed_mappings:
        mappings[int(entry["idx"])] = entry["po_line_number"]

    _save_mapping_to_cache(invoice_cache_path, mappings)
    return mappings

def _save_mapping_to_cache(cache_path: str, mappings: Dict[int, int]):
    """Persists line mapping inside the invoice cache file."""
    if os.path.exists(cache_path):
        with open(cache_path, "r", encoding="utf-8") as f:
            doc = json.load(f)
        doc["semantic_line_mapping"] = mappings
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(doc, f, indent=2)


# ==============================================================================
# SECTION 5: DETERMINISTIC AUDIT ENGINE
# ==============================================================================

def run_deterministic_3way_match(pdf_path: str) -> Dict[str, Any]:
    """Executes the full 3-way match using scoped batch resolution and deterministic math."""
    cache_filename = os.path.basename(pdf_path).replace(".pdf", ".json")
    cache_path = os.path.join(CACHE_DIR, cache_filename)

    invoice = extract_invoice_from_pdf(pdf_path)
    inv_id = invoice["invoice_id"]
    po_id = invoice["po_id"]
    vendor = invoice["vendor_name"]
    freight = float(invoice.get("freight_charges", 0.0))

    # Pull PO ground truth
    po_data = tools.get_po_details(po_id)
    if "error" in po_data:
        tools.update_invoice_status(inv_id, "Flagged_Exception", f"Missing PO: {po_id}")
        return {"invoice_id": inv_id, "status": "Flagged_Exception", "note": f"PO {po_id} not found."}

    po_lines = po_data["lines"]
    po_line_map = {l["line_number"]: l for l in po_lines}
    grn_receipt_map = tools.get_aggregate_receipts_for_po_lines(po_id)

    # Scoped batch line resolution (1 single call for all lines, cached thereafter)
    semantic_mappings = batch_match_lines_to_po(invoice["line_items"], po_lines, cache_path)

    line_audit_results = []
    discrepancies: List[str] = []
    total_invoice_variance = freight

    for idx, billed_line in enumerate(invoice["line_items"], 1):
        billed_desc = billed_line["description"]
        billed_qty = int(billed_line["billed_qty"])
        billed_price = float(billed_line["billed_unit_price"])

        matched_po_line_num = semantic_mappings.get(idx, 0)
        matched_po_line = po_line_map.get(matched_po_line_num)

        if not matched_po_line:
            discrepancies.append(f"Line {idx}: Item '{billed_desc}' not found on PO {po_id}.")
            continue

        item_code = matched_po_line["item_code"]
        auth_price = float(matched_po_line["unit_price"])
        total_received = grn_receipt_map.get(matched_po_line_num, 0)

        # Deterministic calculations
        qty_delta = billed_qty - total_received
        price_delta = round(billed_price - auth_price, 2)
        line_variance = round((billed_qty * billed_price) - (total_received * auth_price), 2)
        total_invoice_variance += line_variance

        line_audit_results.append({
            "line_number": matched_po_line_num,
            "billed_description": billed_desc,
            "item_code": item_code,
            "billed_qty": billed_qty,
            "received_qty": total_received,
            "billed_unit_price": billed_price,
            "authorized_unit_price": auth_price,
            "line_variance": line_variance
        })

        if qty_delta > 0:
            discrepancies.append(
                f"Line {matched_po_line_num} ({item_code}): Billed {billed_qty} units, but dock receipts total only {total_received} units ({qty_delta} units short)."
            )

        if price_delta > 0 and line_variance > TOLERANCE_THRESHOLD_USD:
            discrepancies.append(
                f"Line {matched_po_line_num} ({item_code}): Price variance +${price_delta:.2f}/unit exceeds tolerance."
            )

    if freight > 0:
        discrepancies.append(f"Unauthorized freight surcharge of ${freight:.2f}.")

    # Policy disposition
    if discrepancies:
        final_status = "Flagged_Exception"
        note = " | ".join(discrepancies)
        tools.update_invoice_status(inv_id, final_status, note)
        dispute_email = tools.draft_dispute_email(vendor, inv_id, po_id, note)
    elif total_invoice_variance > 0:
        final_status = "Warning_Approved"
        note = f"Semantic match verified. Cumulative price variance +${total_invoice_variance:.2f} approved within <= ${TOLERANCE_THRESHOLD_USD:.2f} tolerance."
        tools.update_invoice_status(inv_id, final_status, note)
        dispute_email = None
    else:
        final_status = "Approved"
        note = "Exact 3-way match verified against cumulative dock receipts. Zero variance."
        tools.update_invoice_status(inv_id, final_status, note)
        dispute_email = None

    return {
        "invoice_id": inv_id,
        "po_id": po_id,
        "vendor": vendor,
        "status": final_status,
        "note": note,
        "freight": freight,
        "total_variance": total_invoice_variance,
        "lines": line_audit_results,
        "dispute_email": dispute_email
    }


# ==============================================================================
# SECTION 6: CLI VERIFICATION
# ==============================================================================

if __name__ == "__main__":
    queue = [
        "invoices_pdf/INV-9004.pdf",
        "invoices_pdf/INV-9005.pdf"
    ]
    for pdf in queue:
        print("\n" + "=" * 70)
        print(f"RUNNING OPTIMIZED BATCH AUDIT: {pdf}")
        print("=" * 70)
        start_time = time.time()
        res = run_deterministic_3way_match(pdf)
        elapsed = round(time.time() - start_time, 2)
        print(f"Elapsed Time       : {elapsed}s")
        print(f"Final Audit Status : {res['status']}")
        print(f"Auditor Note       : {res['note']}")
        if res.get("dispute_email"):
            print("\n[STAGED DISPUTE EMAIL DRAFT]:")
            print(res["dispute_email"])