"""Tool 1: Read text from PDFs, including a limited scanned-page image fallback."""
import base64
import fitz
from langchain_core.tools import tool

@tool
def read_documents(pdf_bytes: bytes) -> dict:
    """Read a PDF and return its text and base64 page images if text is sparse."""
    if not pdf_bytes.startswith(b"%PDF"):
        raise ValueError("Upload a valid PDF file.")
    document = fitz.open(stream=pdf_bytes, filetype="pdf")
    try:
        if document.page_count < 1 or document.page_count > 5:
            raise ValueError("PDF must contain 1 to 5 pages.")
        text = "\n".join(page.get_text(sort=True) for page in document)
        images = []
        if len(text.strip()) < 60:
            for page in document:
                pix = page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5), alpha=False)
                images.append(base64.b64encode(pix.tobytes("png")).decode("ascii"))
        return {"pdf_text": text[:30000], "page_images": images, "page_count": document.page_count}
    finally:
        document.close()
