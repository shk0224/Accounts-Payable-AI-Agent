
"""FastAPI app following InvoiceFlow's app.py layout."""

# ==========================================
# SECTION 1: IMPORTS
# Purpose: Import required Python libraries and project modules
# ==========================================

from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from backend import run_audit_batch
from database import (
    initialize_database,
    save_audit_history,
    list_audit_history,
    get_audit_history,
    delete_audit_history
)


# ==========================================
# SECTION 2: FASTAPI APP SETUP
# Purpose: Create the FastAPI application and serve static files
# ==========================================

PROJECT_ROOT = Path(__file__).resolve().parent

app = FastAPI(title="Accounts Payable AI Agent")

app.mount(
    "/static",
    StaticFiles(directory=str(PROJECT_ROOT / "static")),
    name="static"
)

MAX_FILES = 10

MAX_SIZE = 10 * 1024 * 1024

initialize_database()


# ==========================================
# SECTION 3: FASTAPI ENDPOINT 1 - HOME PAGE
# Method: GET /
# Purpose: Return the user interface
# ==========================================

@app.get("/", response_class=HTMLResponse)
def home():

    return (
        PROJECT_ROOT / "templates" / "index.html"
    ).read_text(encoding="utf-8")


# ==========================================
# SECTION 4: FASTAPI ENDPOINT 2 - HEALTH CHECK
# Method: GET /health
# Purpose: Check that the API is running
# ==========================================

@app.get("/health")
def health():

    return {
        "status": "ok"
    }


# ==========================================
# SECTION 5: FASTAPI ENDPOINT 3 - PROCESS DOCUMENTS
# Method: POST /api/process
# Purpose: Accept multiple PDFs, call LangGraph, and save history
# ==========================================

@app.post("/api/process")
async def process(
    user_query: str = Form(...),
    invoices: list[UploadFile] = File(...),
    purchase_orders: list[UploadFile] | None = File(None)
):

    # ------------------------------------------
    # STEP 1: Validate user question
    # ------------------------------------------

    if not user_query.strip():

        raise HTTPException(
            status_code=400,
            detail="Enter a question"
        )


    # ------------------------------------------
    # STEP 2: Validate number of invoices
    # ------------------------------------------

    if len(invoices) == 0 or len(invoices) > MAX_FILES:

        raise HTTPException(
            status_code=400,
            detail="Upload between 1 and 10 invoices"
        )


    # ------------------------------------------
    # STEP 3: Validate purchase order count
    # ------------------------------------------

    po_files = purchase_orders or []

    if len(po_files) not in (0, len(invoices)):

        raise HTTPException(
            status_code=400,
            detail=(
                "Upload either zero purchase orders or "
                "one purchase order per invoice"
            )
        )


    # ------------------------------------------
    # STEP 4: Helper function - Read PDF safely
    # ------------------------------------------

    async def get_pdf(upload: UploadFile) -> bytes:

        if not (upload.filename or "").lower().endswith(".pdf"):

            raise HTTPException(
                status_code=400,
                detail="Only PDF files are supported"
            )

        data = await upload.read(MAX_SIZE + 1)

        if len(data) > MAX_SIZE:

            raise HTTPException(
                status_code=400,
                detail="Each PDF must be at most 10 MB"
            )

        if not data.startswith(b"%PDF"):

            raise HTTPException(
                status_code=400,
                detail="Invalid PDF file"
            )

        return data


    # ------------------------------------------
    # STEP 5: Read all invoice PDFs
    # ------------------------------------------

    invoice_data = []

    for invoice in invoices:

        invoice_bytes = await get_pdf(invoice)

        invoice_data.append(
            (invoice.filename, invoice_bytes)
        )


    # ------------------------------------------
    # STEP 6: Read all purchase order PDFs
    # ------------------------------------------

    po_data = []

    for purchase_order in po_files:

        po_bytes = await get_pdf(purchase_order)

        po_data.append(
            (purchase_order.filename, po_bytes)
        )


    # ------------------------------------------
    # STEP 7: Pair invoices with purchase orders
    # ------------------------------------------

    document_pairs = []

    for index, (invoice_filename, invoice_bytes) in enumerate(invoice_data):

        if po_data:

            po_filename, po_bytes = po_data[index]

        else:

            po_filename = ""
            po_bytes = b""

        document_pairs.append(
            (
                invoice_filename,
                invoice_bytes,
                po_filename,
                po_bytes
            )
        )


    # ------------------------------------------
    # STEP 8: Execute LangGraph batch processing
    # ------------------------------------------

    try:

        batch_result = run_audit_batch(
            user_query,
            document_pairs
        )

    except Exception as exc:

        # Avoid exposing secrets or internal stack traces.
        print(
            f"Batch processing failed: {type(exc).__name__}"
        )

        raise HTTPException(
            status_code=500,
            detail=(
                "Processing failed. Check server logs "
                "and your OpenAI configuration."
            )
        ) from exc

    # Save results after successful LangGraph execution.
    # If database storage fails, return the completed audit anyway.
    try:
        save_audit_history(user_query, batch_result)
    except Exception as exc:
        print(f"History save failed: {type(exc).__name__}")

    return JSONResponse(batch_result)


# ==========================================
# SECTION 6: FASTAPI ENDPOINT 4 - LIST HISTORY
# Method: GET /api/history
# Purpose: Show previous audit questions in sidebar
# ==========================================

@app.get("/api/history")
def history_list():
    return list_audit_history()


# ==========================================
# SECTION 7: FASTAPI ENDPOINT 5 - OPEN HISTORY
# Method: GET /api/history/{history_id}
# Purpose: Reopen a previous question and audit result
# ==========================================

@app.get("/api/history/{history_id}")
def history_detail(history_id: int):
    session = get_audit_history(history_id)
    if session is None:
        raise HTTPException(status_code=404, detail="History not found")
    return session


# ==========================================
# SECTION 8: FASTAPI ENDPOINT 6 - DELETE HISTORY
# Method: DELETE /api/history/{history_id}
# Purpose: Delete a previous audit session
# ==========================================

@app.delete("/api/history/{history_id}")
def history_delete(history_id: int):
    if not delete_audit_history(history_id):
        raise HTTPException(status_code=404, detail="History not found")
    return {"deleted": True}


# ==========================================
# SECTION 9: RUN FASTAPI SERVER
# Purpose: Start the development web server
# ==========================================

if __name__ == "__main__":

    import uvicorn

    uvicorn.run(
        app,
        host="127.0.0.1",
        port=8000
    )
