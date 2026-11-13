# Accounts Payable AI Agent

An AI-powered Accounts Payable auditing application built with **OpenAI, LangGraph, and FastAPI**. It compares supplier invoices against purchase orders, identifies billing discrepancies, and generates structured audit reports for human review.

![Python](https://img.shields.io/badge/Python-3.11-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-API-009688)
![LangGraph](https://img.shields.io/badge/LangGraph-Agent_Workflow-purple)
![OpenAI](https://img.shields.io/badge/OpenAI-gpt--4o--mini-black)
![License](https://img.shields.io/badge/License-MIT-green)

![Audit results dashboard](docs/audit-results.png)

---

## 1. Business Problem

Accounts Payable (AP) teams regularly receive invoices from suppliers and must verify them against purchase orders before processing payments.

This involves checking:

- Whether the purchase order number referenced on the invoice matches the purchase order.
- Whether supplier information is consistent.
- Whether product quantities and unit prices are correct.
- Whether invoice totals match purchase order totals.
- Whether any discrepancies require further investigation.

Manually reviewing large numbers of invoices can be time-consuming, repetitive, and prone to human error.

**The challenge:** How can businesses automate the initial invoice verification process while keeping humans responsible for final payment decisions?

---

## 2. Proposed Solution

**Accounts Payable AI Agent** automates the first-pass invoice auditing workflow using AI-powered document extraction and Python-based validation.

Users upload invoice PDFs and, optionally, the corresponding purchase order PDFs, submit an audit request in plain English, and receive structured results.

The system:

1. Understands the user's request using an OpenAI-powered router.
2. Extracts structured information from the uploaded PDF documents.
3. Compares invoice details with purchase order information.
4. Calculates financial discrepancies using Python tools.
5. Generates an audit report with findings and a recommended action.

The application supports human review. It does not approve or execute payments.

---

## 3. Key Features

- **Batch PDF Processing:** Upload 1 to 10 invoices, plus either no purchase orders or exactly one purchase order per invoice. Maximum size is 10 MB per PDF.
- **AI-Powered Document Extraction:** Extracts the document number, referenced PO number, vendor, currency, total, and line items (SKU, description, quantity, unit price). Both the PDF text and rendered page images are sent to the model.
- **No Invented Data:** The extraction prompt instructs the model to leave missing fields blank instead of guessing.
- **Natural Language Requests:** The router classifies each request as information extraction, document matching, or a full financial audit.
- **Purchase Order Matching:** Compares document identities and line-item information.
- **Financial Variance Detection:** Identifies price, quantity, and total amount differences using Python-based calculations.
- **Conditional Workflow:** LangGraph runs only the nodes that the request requires.
- **Audit Reports:** Shows the audit status, document total difference, identified issues, and recommended action for each invoice.
- **Execution Trace:** Every result records the LangGraph nodes that ran and what each one found.
- **Batch Error Handling:** If one invoice fails, the remaining invoices are still processed.
- **Input Validation:** Checks file extension, PDF file signature, file size, and file counts before any document is sent to the model.
- **Audit History:** Saves each batch to SQLite so it can be reopened or deleted from the sidebar.
- **Web Dashboard:** Upload documents, review results, and access audit history in the browser.

---

## 4. Architecture at a Glance

| Component | Implementation |
|---|---|
| AI Agent | 1 |
| Custom Tools | 4 |
| LangGraph Nodes | 5 |
| Conditional Routing Functions | 2 |
| Workflow Type | Conditional |
| LLM | OpenAI GPT-4o-mini (configurable, temperature 0) |
| Backend | Python + FastAPI |
| Database | SQLite |

### Workflow Architecture

The application uses **one AI-powered LangGraph workflow** with five nodes and four custom tools. The workflow is conditional rather than a fixed sequential pipeline: based on the user's request, LangGraph selects which nodes to run.

![LangGraph workflow](docs/architecture.svg)

### LangGraph Nodes

| Node | Responsibility | Uses |
|---|---|---|
| `router` | Classifies the request as `info`, `match`, or `audit`. Ambiguous financial questions default to `audit`. | LLM with structured output |
| `document_reader` | Extracts invoice and purchase order fields | `read_documents` tool + LLM |
| `po_matcher` | Matches document identities and line items | `match_purchase_order` tool |
| `variance_checker` | Calculates financial differences | `calculate_variance` tool |
| `audit_reporter` | Generates the final status, issues, and recommendation | `generate_audit_report` tool |

### Custom Tools

| Tool | Purpose |
|---|---|
| `read_documents` | Extracts PDF text and page images |
| `match_purchase_order` | Compares invoice and purchase order information |
| `calculate_variance` | Calculates price, quantity, and total differences |
| `generate_audit_report` | Creates structured audit findings and recommendations |

### Conditional Routing

Two routing functions decide which node runs next:

- `route_after_reader`: sends `info` requests directly to the reporter, and everything else to the PO matcher.
- `route_after_matcher`: sends `audit` requests to the variance checker, and `match` requests to the reporter.

| Request Type | Execution Path | Possible Status |
|---|---|---|
| Information | Router → Document Reader → Audit Reporter | `INFORMATION_ONLY` |
| Matching | Router → Document Reader → PO Matcher → Audit Reporter | `IDENTITY_MATCH_ONLY` when identities match (financial values are not audited) |
| Full Financial Audit | Router → Document Reader → PO Matcher → Variance Checker → Audit Reporter | `MATCHED` or `FLAGGED_FOR_REVIEW` |

If an invoice cannot be processed, its result is marked `FAILED` and the rest of the batch continues. If no purchase order is supplied, the matcher and variance checker report it as an issue instead of guessing.

---

## 5. Example Audit Results

The examples below are actual results from the application using the sample documents `01_Perfect_Match` and `02_Price_Mismatch`.

### Example 1: Matched Invoice

**Invoice:** INV-1001
**Purchase Order:** PO-1001

| Field | Result |
|---|---|
| Audit Status | `MATCHED` |
| Document Total Difference | $0.00 |
| Issues | None detected in the checked fields |
| Recommended Action | No mismatch detected within checked fields; payment still requires normal approval |

### Example 2: Price Mismatch

**Invoice:** INV-1002
**Purchase Order:** PO-1002

| Field | Result |
|---|---|
| Audit Status | `FLAGGED_FOR_REVIEW` (shown as *Needs Review* in the dashboard) |
| Document Total Difference | +$200.00 |
| Issues | Unit price mismatch for sku-b202; Document total difference: +200.00 |
| Recommended Action | Human review required before payment |

### Execution Trace

Each result includes the path the agent took. Trace for Example 2:

```json
[
  { "node": "router", "result": "audit" },
  { "node": "document_reader", "result": "Invoice extracted; PO extracted" },
  { "node": "po_matcher", "result": "0 matching issues" },
  { "node": "variance_checker", "result": "2 financial issues" },
  { "node": "audit_reporter", "result": "FLAGGED_FOR_REVIEW" }
]
```

---

## 6. Technology Stack

| Category | Technology |
|---|---|
| Programming Language | Python 3.11 |
| AI Model | OpenAI GPT-4o-mini |
| Agent Orchestration | LangGraph |
| LLM Integration | LangChain (`langchain-openai`, `langchain-core`) |
| Structured Data Validation | Pydantic |
| Backend Framework | FastAPI |
| API Server | Uvicorn |
| PDF Processing | PyMuPDF |
| Database | SQLite |
| Frontend | HTML, CSS, JavaScript |

---

## 7. Project Structure

```text
Accounts-Payable-AI-Agent/
|
|-- app.py
|-- backend.py
|-- database.py
|-- template.py
|-- requirements.txt
|-- .env.example
|-- .gitignore
|-- README.md
|-- LICENSE
|
|-- tools/
|   |-- __init__.py
|   |-- document_reader.py
|   |-- po_matcher.py
|   |-- variance_calculator.py
|   |-- audit_reporter.py
|
|-- templates/
|   |-- index.html
|
|-- static/
|   |-- style.css
|
|-- docs/
|   |-- architecture.svg
|   |-- audit-results.png
|   |-- document-upload.png
|
|-- test_data/
|   |-- invoices/
|   |-- purchase_orders/
|
|-- tests/
|
|-- output/
```

### Important Files

- **app.py:** FastAPI application, upload validation, API endpoints, and audit history integration.
- **backend.py:** LangGraph state, nodes, conditional routing, graph compilation, and batch execution.
- **database.py:** SQLite operations for saving, listing, retrieving, and deleting audit history.
- **tools/:** Custom Python tools for document reading, matching, variance calculation, and reporting.
- **templates/index.html:** Web dashboard.
- **static/style.css:** Dashboard styling.
- **template.py:** Creates the project folder and file structure.

The SQLite database file (`audit_history.db`) is created automatically on first run and is not committed to the repository.

---

## 8. Getting Started

### Step 1: Clone the Repository

```bash
git clone https://github.com/YOUR_USERNAME/Accounts-Payable-AI-Agent.git
cd Accounts-Payable-AI-Agent
```

Replace `YOUR_USERNAME` with your GitHub username.

### Step 2: Create a Python Environment

```bash
conda create -n ap-agent python=3.11 -y
conda activate ap-agent
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 4: Configure Environment Variables

Create a `.env` file in the project root (you can copy `.env.example`):

```env
OPENAI_API_KEY=your_openai_api_key
OPENAI_MODEL=gpt-4o-mini
```

`OPENAI_MODEL` is optional and defaults to `gpt-4o-mini`. Keep API keys private and never commit the `.env` file.

### Step 5: Run the Application

```bash
python app.py
```

Then open **http://127.0.0.1:8000** in your browser.

### Step 6: Use the AI Agent

![Document upload screen](docs/document-upload.png)

1. Upload one or more invoice PDFs.
2. Optionally upload the corresponding purchase order PDFs **in the same order** as the invoices.
3. Enter your audit question.
4. Click **Run AI Agent**.
5. Review the audit summary, issues, and recommended actions.

**Example question:**

> Audit these invoices against their purchase orders and flag discrepancies, including price, quantity, and total amount differences.

---

## 9. API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/` | Load the application dashboard |
| GET | `/health` | Check application health |
| POST | `/api/process` | Process an invoice audit batch |
| GET | `/api/history` | Retrieve the 100 most recent audits |
| GET | `/api/history/{history_id}` | Retrieve a specific audit |
| DELETE | `/api/history/{history_id}` | Delete an audit history record |

`POST /api/process` accepts a multipart form with these fields:

| Field | Required | Description |
|---|---|---|
| `user_query` | Yes | The audit request in plain English |
| `invoices` | Yes | 1 to 10 invoice PDFs |
| `purchase_orders` | No | Either none, or exactly one PDF per invoice |

Example request:

```bash
curl -X POST http://127.0.0.1:8000/api/process \
  -F "user_query=Audit these invoices against their purchase orders" \
  -F "invoices=@test_data/invoices/02_Price_Mismatch_Invoice.pdf" \
  -F "purchase_orders=@test_data/purchase_orders/02_Price_Mismatch_PO.pdf"
```

Internal errors and stack traces are not returned to the client.

---

## 10. Design Principles

### AI for Understanding, Python for Calculation

OpenAI is used for request classification and structured document extraction. Custom Python tools handle purchase order matching and financial variance calculations.

This separates language understanding from financial calculation logic, although overall accuracy still depends on correct document extraction.

### Conditional Agent Execution

LangGraph selects the appropriate path based on the user's request and skips nodes that are not needed.

### Human-in-the-Loop Decision Making

The agent provides audit findings and recommendations but does not approve supplier payments. Even a `MATCHED` invoice still requires normal approval.

### Traceable Execution

Each result includes a trace of the LangGraph nodes executed, so users can see how the result was produced.

---

## 11. Current Limitations

- Invoice and purchase order files are paired by upload order, not by the PO number on the invoice.
- The application performs two-way matching (invoice and purchase order). Goods receipts are not included.
- Batch documents are processed sequentially.
- There is no user authentication or user-specific audit history.
- SQLite audit history is stored locally and requires persistent storage when deployed.
- AI-based extraction accuracy may vary depending on PDF quality and document formatting.

The current implementation is intended for development, demonstration, and further validation before production use.

---

## 12. Future Improvements

- [ ] Automatic invoice-to-PO pairing using document identifiers
- [ ] Three-way matching with goods receipt documents
- [ ] Show invoice and PO values (price, quantity) for each flagged line item
- [ ] Duplicate invoice detection
- [ ] Configurable variance tolerances for rounding and tax differences
- [ ] User authentication and private audit history
- [ ] Extraction accuracy evaluation on a labeled test set
- [ ] Parallel batch processing
- [ ] Cloud deployment with persistent database storage

---

## 13. License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.