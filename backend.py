
"""One OpenAI-powered LangGraph agent, five nodes, four custom tools."""

# ==========================================
# SECTION 1: IMPORTS
# Purpose: Import required Python libraries and project modules
# ==========================================

import os

from typing import TypedDict, Literal

from pydantic import BaseModel, Field
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import StateGraph, START, END

from tools import (
    read_documents,
    match_purchase_order,
    calculate_variance,
    generate_audit_report
)

load_dotenv()


# ==========================================
# SECTION 2: LLM AND STRUCTURED OUTPUT MODELS
# Purpose: Initialize OpenAI and define structured response models
# ==========================================

llm = ChatOpenAI(
    model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
    temperature=0
)


class RouteDecision(BaseModel):

    task: Literal["info", "match", "audit"] = Field(
        description=(
            "info: read only; "
            "match: check identities/items; "
            "audit: full financial check"
        )
    )


class LineItem(BaseModel):

    sku: str = ""
    description: str = ""
    quantity: str = ""
    unit_price: str = ""


class DocumentFields(BaseModel):

    document_number: str = ""
    po_number: str = ""
    vendor: str = ""
    currency: str = ""
    total: str = ""
    items: list[LineItem] = Field(default_factory=list)


# ==========================================
# SECTION 3: LANGGRAPH STATE
# Purpose: Share data between the LangGraph nodes
# ==========================================

class AuditState(TypedDict):

    user_query: str
    invoice_bytes: bytes
    po_bytes: bytes

    task: str

    invoice_data: dict
    po_data: dict

    match_result: dict
    variance_result: dict

    report: dict

    trace: list[dict]


# ==========================================
# SECTION 4: LANGGRAPH NODE 1 - ROUTER
# Purpose: Choose the appropriate workflow based on the user request
# ==========================================

def router_node(state: AuditState) -> dict:

    decision = llm.with_structured_output(RouteDecision).invoke([
        SystemMessage(
            content=(
                "Choose info for questions only about document fields, "
                "match for vendor/PO/item identity matching, and audit "
                "for any pricing, quantities, totals, discrepancies "
                "or complete audits. Default to audit for ambiguous "
                "financial questions."
            )
        ),
        HumanMessage(content=state["user_query"])
    ])

    return {
        "task": decision.task,
        "trace": state["trace"] + [
            {
                "node": "router",
                "result": decision.task
            }
        ]
    }


# ==========================================
# SECTION 5: LANGGRAPH NODE 2 - READER
# Purpose: Read invoice and purchase order documents
# ==========================================

# Helper: Extract fields from an invoice or purchase order

def extract_document(pdf_bytes: bytes, kind: str) -> dict:

    content = read_documents.invoke({
        "pdf_bytes": pdf_bytes
    })

    message_parts = [
        {
            "type": "text",
            "text": (
                f"Extract fields from this {kind} document. "
                "Never invent missing fields. "
                "Use decimal strings for numeric values. "
                "Document number is invoice number for invoice "
                "or PO number for purchase order. "
                "The po_number field is the referenced purchase "
                "order number. Text:\n"
                f"{content['pdf_text']}"
            )
        }
    ]

    for image in content["page_images"]:

        message_parts.append({
            "type": "image_url",
            "image_url": {
                "url": f"data:image/png;base64,{image}"
            }
        })

    extracted = llm.with_structured_output(DocumentFields).invoke([
        SystemMessage(
            content=(
                "You extract structured business document data "
                "accurately. Return blank strings when fields "
                "are absent. Do not assume tax or shipping "
                "is included in line items."
            )
        ),
        HumanMessage(content=message_parts)
    ])

    data = extracted.model_dump()

    if kind == "purchase order" and not data["po_number"]:

        data["po_number"] = data["document_number"]

    return data


def document_reader_node(state: AuditState) -> dict:

    invoice_data = extract_document(
        state["invoice_bytes"],
        "invoice"
    )

    po_data = (
        extract_document(state["po_bytes"], "purchase order")
        if state["po_bytes"]
        else {}
    )

    return {
        "invoice_data": invoice_data,
        "po_data": po_data,
        "trace": state["trace"] + [
            {
                "node": "document_reader",
                "result": (
                    "Invoice extracted; PO " +
                    ("extracted" if po_data else "not supplied")
                )
            }
        ]
    }


# ==========================================
# SECTION 6: LANGGRAPH NODE 3 - MATCHER
# Purpose: Match invoice and purchase order fields and items
# ==========================================

def po_matcher_node(state: AuditState) -> dict:

    if not state["po_data"]:

        result = {
            "issues": ["Purchase order PDF is missing"],
            "pairs": [],
            "matched": False
        }

    else:

        result = match_purchase_order.invoke({
            "invoice": state["invoice_data"],
            "purchase_order": state["po_data"]
        })

    return {
        "match_result": result,
        "trace": state["trace"] + [
            {
                "node": "po_matcher",
                "result": f"{len(result['issues'])} matching issues"
            }
        ]
    }


# ==========================================
# SECTION 7: LANGGRAPH NODE 4 - VARIANCE
# Purpose: Calculate financial differences using the custom tool
# ==========================================

def variance_checker_node(state: AuditState) -> dict:

    if not state["po_data"]:

        result = {
            "issues": [
                "Cannot calculate variance without purchase order"
            ],
            "difference": None,
            "matched": False
        }

    else:

        try:

            result = calculate_variance.invoke({
                "invoice": state["invoice_data"],
                "purchase_order": state["po_data"],
                "pairs": state["match_result"].get("pairs", [])
            })

        except (ValueError, KeyError, TypeError) as exc:

            result = {
                "issues": [
                    f"Missing or invalid numeric data: {exc}"
                ],
                "difference": None,
                "matched": False
            }

    return {
        "variance_result": result,
        "trace": state["trace"] + [
            {
                "node": "variance_checker",
                "result": f"{len(result['issues'])} financial issues"
            }
        ]
    }


# ==========================================
# SECTION 8: LANGGRAPH NODE 5 - REPORTER
# Purpose: Create the final audit result
# ==========================================

def audit_reporter_node(state: AuditState) -> dict:

    if state["task"] == "info":

        report = {
            "status": "INFORMATION_ONLY",
            "invoice": state["invoice_data"],
            "purchase_order": state["po_data"],
            "recommendation": (
                "No matching or financial audit was performed"
            )
        }

    else:

        report = generate_audit_report.invoke({
            "invoice": state["invoice_data"],
            "purchase_order": state["po_data"],
            "match_result": state["match_result"],
            "variance_result": state["variance_result"],
            "task": state["task"]
        })

        if (
            state["task"] == "match"
            and report["status"] == "MATCHED"
        ):

            report["status"] = "IDENTITY_MATCH_ONLY"

            report["recommendation"] = (
                "Identity/item matching passed; "
                "financial values were NOT audited"
            )

    return {
        "report": report,
        "trace": state["trace"] + [
            {
                "node": "audit_reporter",
                "result": report["status"]
            }
        ]
    }


# ==========================================
# SECTION 9: LANGGRAPH WORKFLOW AND CONDITIONAL EDGES
# Purpose: Connect graph nodes and define conditional routing
# ==========================================

# Routing Function 1: Choose next node after document reading

def route_after_reader(state: AuditState) -> str:

    return (
        "audit_reporter"
        if state["task"] == "info"
        else "po_matcher"
    )


# Routing Function 2: Choose next node after document matching

def route_after_matcher(state: AuditState) -> str:

    return (
        "variance_checker"
        if state["task"] == "audit"
        else "audit_reporter"
    )


# Create the graph

graph = StateGraph(AuditState)


# Register graph nodes

graph.add_node("router", router_node)

graph.add_node("document_reader", document_reader_node)

graph.add_node("po_matcher", po_matcher_node)

graph.add_node("variance_checker", variance_checker_node)

graph.add_node("audit_reporter", audit_reporter_node)


# Connect graph edges

graph.add_edge(START, "router")

graph.add_edge("router", "document_reader")

graph.add_conditional_edges(
    "document_reader",
    route_after_reader,
    {
        "po_matcher": "po_matcher",
        "audit_reporter": "audit_reporter"
    }
)

graph.add_conditional_edges(
    "po_matcher",
    route_after_matcher,
    {
        "variance_checker": "variance_checker",
        "audit_reporter": "audit_reporter"
    }
)

graph.add_edge("variance_checker", "audit_reporter")

graph.add_edge("audit_reporter", END)


# ==========================================
# SECTION 10: COMPILE
# Purpose: Compile the LangGraph workflow
# ==========================================

app_graph = graph.compile()


# ==========================================
# SECTION 11: FASTAPI TO LANGGRAPH CONNECTION (INVOKE)
# Purpose: Invoke the compiled graph from the FastAPI application
# ==========================================

def run_audit_agent(
    user_query: str,
    invoice_bytes: bytes,
    po_bytes: bytes = b""
) -> dict:

    initial_state: AuditState = {

        "user_query": user_query,

        "invoice_bytes": invoice_bytes,
        "po_bytes": po_bytes,

        "task": "",

        "invoice_data": {},
        "po_data": {},

        "match_result": {},
        "variance_result": {},

        "report": {},

        "trace": []
    }

    result = app_graph.invoke(initial_state)

    return {
        "task": result["task"],
        "report": result["report"],
        "trace": result["trace"]
    }


# ==========================================
# SECTION 12: BATCH INVOICE PROCESSING
# Purpose: Process multiple invoices through the existing graph
# ==========================================

def run_audit_batch(
    user_query: str,
    document_pairs: list[tuple[str, bytes, str, bytes]]
) -> dict:

    results = []

    completed = 0
    failed = 0

    for (
        invoice_filename,
        invoice_bytes,
        po_filename,
        po_bytes
    ) in document_pairs:

        try:

            # Execute the existing LangGraph agent

            audit_result = run_audit_agent(
                user_query,
                invoice_bytes,
                po_bytes
            )

            # Save the individual invoice result

            results.append({
                "filename": invoice_filename,
                "purchase_order_filename": po_filename,
                "task": audit_result["task"],
                "report": audit_result["report"],
                "trace": audit_result["trace"]
            })

            completed += 1

        except Exception as exc:

            # Continue processing remaining invoices.
            # Do not expose internal errors to the frontend.

            print(
                f"Invoice processing failed: {type(exc).__name__}"
            )

            results.append({
                "filename": invoice_filename,
                "purchase_order_filename": po_filename,
                "task": "",
                "report": {
                    "status": "FAILED",
                    "recommendation": (
                        "Processing failed. Check server logs "
                        "and your OpenAI configuration."
                    )
                },
                "trace": []
            })

            failed += 1

    return {
        "total": len(document_pairs),
        "completed": completed,
        "failed": failed,
        "results": results
    }
