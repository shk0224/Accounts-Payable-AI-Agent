"""Tool 4: Produce a stable, explainable report."""
from langchain_core.tools import tool

@tool
def generate_audit_report(invoice: dict, purchase_order: dict, match_result: dict, variance_result: dict, task: str) -> dict:
    """Combine audit findings; never auto-approve a payment."""
    issues = list(dict.fromkeys(match_result.get("issues", []) + variance_result.get("issues", [])))
    status = "FLAGGED_FOR_REVIEW" if issues else "MATCHED"
    return {"status": status, "task": task, "invoice_number": invoice.get("document_number", ""), "po_number": purchase_order.get("document_number", ""), "issues": issues, "difference": variance_result.get("difference"), "recommendation": "Human review required before payment" if issues else "No mismatch detected within checked fields; payment still requires normal approval"}
