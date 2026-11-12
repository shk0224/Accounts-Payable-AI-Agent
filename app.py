"""FastAPI app following InvoiceFlow's app.py layout."""
import json
from pathlib import Path
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from backend import run_audit_agent

PROJECT_ROOT = Path(__file__).resolve().parent
app = FastAPI(title="Accounts Payable AI Agent")
app.mount("/static", StaticFiles(directory=str(PROJECT_ROOT / "static")), name="static")

@app.get("/", response_class=HTMLResponse)
def home():
    return (PROJECT_ROOT / "templates" / "index.html").read_text(encoding="utf-8")

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/api/process")
async def process(user_query: str = Form(...), invoice: UploadFile = File(...), purchase_order: UploadFile | None = File(None)):
    async def get_pdf(upload: UploadFile) -> bytes:
        if not (upload.filename or "").lower().endswith(".pdf"):
            raise HTTPException(400, "Only PDF files are supported")
        data = await upload.read(10 * 1024 * 1024 + 1)
        if len(data) > 10 * 1024 * 1024:
            raise HTTPException(400, "Each PDF must be at most 10 MB")
        if not data.startswith(b"%PDF"):
            raise HTTPException(400, "Invalid PDF file")
        return data
    if not user_query.strip():
        raise HTTPException(400, "Enter a question")
    invoice_bytes = await get_pdf(invoice)
    po_bytes = await get_pdf(purchase_order) if purchase_order else b""
    try:
        return JSONResponse(run_audit_agent(user_query, invoice_bytes, po_bytes))
    except Exception as exc:
        # Avoid exposing provider secrets or internal stack traces to users.
        print(f"Processing failed: {type(exc).__name__}: {exc}")
        raise HTTPException(500, "Processing failed. Check server logs and your OpenAI configuration.") from exc

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
