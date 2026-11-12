"""Tool 2: Match invoice to PO without trusting the LLM for comparisons."""
from langchain_core.tools import tool

def normalize(value):
    return " ".join(str(value or "").casefold().split())

@tool
def match_purchase_order(invoice: dict, purchase_order: dict) -> dict:
    """Match PO reference, vendor, currency, and item SKUs or descriptions."""
    issues = []
    for field in ("po_number", "vendor", "currency"):
        if not normalize(invoice.get(field)) or not normalize(purchase_order.get(field)):
            issues.append(f"Missing {field} in invoice or PO")
        elif normalize(invoice[field]) != normalize(purchase_order[field]):
            issues.append(f"{field} mismatch: invoice={invoice[field]}, PO={purchase_order[field]}")
    invoice_items = invoice.get("items") or []
    po_items = purchase_order.get("items") or []
    if not invoice_items or not po_items:
        issues.append("Missing line items")
    pairs = []
    used = set()
    for inv in invoice_items:
        key = normalize(inv.get("sku") or inv.get("description"))
        matches = [(i, po) for i, po in enumerate(po_items) if i not in used and key and key == normalize(po.get("sku") or po.get("description"))]
        if len(matches) == 1:
            i, po = matches[0]
            used.add(i)
            pairs.append({"invoice": inv, "po": po, "item": key})
        else:
            issues.append(f"Unmatched or ambiguous invoice item: {key or '[blank]'}")
    for i, po in enumerate(po_items):
        if i not in used:
            issues.append(f"PO item not matched: {po.get('sku') or po.get('description')}")
    return {"issues": issues, "pairs": pairs, "matched": not issues}
