"""Tool 3: Exact decimal financial comparisons."""
from decimal import Decimal, InvalidOperation
from langchain_core.tools import tool

def money(value):
    try:
        number = Decimal(str(value))
        if not number.is_finite():
            raise ValueError("Non-finite number")
        return number
    except (InvalidOperation, TypeError, ValueError):
        raise ValueError(f"Invalid financial number: {value}")

@tool
def calculate_variance(invoice: dict, purchase_order: dict, pairs: list) -> dict:
    """Check quantities, prices, line totals, and document totals using Decimal."""
    issues = []
    inv_sum = Decimal("0")
    po_sum = Decimal("0")
    for item in invoice.get("items", []):
        quantity, price = money(item.get("quantity")), money(item.get("unit_price"))
        if quantity < 0 or price < 0:
            issues.append("Negative invoice quantity or price")
        inv_sum += quantity * price
    for item in purchase_order.get("items", []):
        quantity, price = money(item.get("quantity")), money(item.get("unit_price"))
        if quantity < 0 or price < 0:
            issues.append("Negative PO quantity or price")
        po_sum += quantity * price
    for pair in pairs:
        inv, po = pair["invoice"], pair["po"]
        if money(inv["quantity"]) != money(po["quantity"]):
            issues.append(f"Quantity mismatch for {pair['item']}")
        if money(inv["unit_price"]) != money(po["unit_price"]):
            issues.append(f"Unit price mismatch for {pair['item']}")
    inv_total, po_total = money(invoice.get("total")), money(purchase_order.get("total"))
    if abs(inv_sum - inv_total) > Decimal("0.01"):
        issues.append("Invoice total does not equal sum of its lines (tax/shipping not modeled)")
    if abs(po_sum - po_total) > Decimal("0.01"):
        issues.append("PO total does not equal sum of its lines (tax/shipping not modeled)")
    difference = inv_total - po_total
    if abs(difference) > Decimal("0.01"):
        issues.append(f"Document total difference: {difference:+.2f}")
    return {"issues": issues, "invoice_total": str(inv_total), "po_total": str(po_total), "difference": str(difference), "matched": not issues}
