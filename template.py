
from pathlib import Path

# Project root directory
PROJECT_ROOT = Path(__file__).resolve().parent

# Folder structure
folders = [
    "tools",
    "templates",
    "static",
    "test_data/invoices",
    "test_data/purchase_orders",
    "tests",
    "output",
]

# File structure
files = [
    "app.py",
    "backend.py",
    "requirements.txt",
    ".env.example",
    ".gitignore",
    "README.md",
    "tools/__init__.py",
    "tools/document_reader.py",
    "tools/po_matcher.py",
    "tools/variance_calculator.py",
    "tools/audit_reporter.py",
    "templates/index.html",
    "static/style.css",
    "tests/test_audit.py",
    "test_data/expected_results.json",
]

# Create folders
for folder in folders:
    folder_path = PROJECT_ROOT / folder
    folder_path.mkdir(parents=True, exist_ok=True)
    print(f"Folder created: {folder}")

# Create files
for file in files:
    file_path = PROJECT_ROOT / file
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.touch(exist_ok=True)
    print(f"File ready: {file}")

print("\nAccounts-Payable-AI-Agent project structure created successfully!")
