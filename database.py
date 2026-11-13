
"""SQLite storage for Accounts Payable AI audit history."""

# ==========================================
# SECTION 1: IMPORTS
# Purpose: Import built-in database and JSON libraries
# ==========================================

import json
import sqlite3
from pathlib import Path


# ==========================================
# SECTION 2: DATABASE CONFIGURATION
# Purpose: Keep saved history in the project directory
# ==========================================

DATABASE_PATH = Path(__file__).resolve().parent / "audit_history.db"


# ==========================================
# SECTION 3: INITIALIZE DATABASE
# Purpose: Create the history table when missing
# ==========================================

def initialize_database():
    with sqlite3.connect(DATABASE_PATH) as connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS audit_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_query TEXT NOT NULL,
                batch_result TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
            )
        """)


# ==========================================
# SECTION 4: SAVE AUDIT HISTORY
# Purpose: Store question and completed batch result
# ==========================================

def save_audit_history(user_query: str, batch_result: dict) -> int:
    with sqlite3.connect(DATABASE_PATH) as connection:
        cursor = connection.execute(
            "INSERT INTO audit_history (user_query, batch_result) VALUES (?, ?)",
            (user_query, json.dumps(batch_result))
        )
        return cursor.lastrowid


# ==========================================
# SECTION 5: LIST AUDIT HISTORY
# Purpose: Retrieve sidebar summaries, newest first
# ==========================================

def list_audit_history() -> list[dict]:
    with sqlite3.connect(DATABASE_PATH) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(
            "SELECT id, user_query, created_at FROM audit_history ORDER BY id DESC LIMIT 100"
        ).fetchall()
        return [dict(row) for row in rows]


# ==========================================
# SECTION 6: GET AUDIT HISTORY
# Purpose: Retrieve the saved batch report for one session
# ==========================================

def get_audit_history(history_id: int) -> dict | None:
    with sqlite3.connect(DATABASE_PATH) as connection:
        connection.row_factory = sqlite3.Row
        row = connection.execute(
            "SELECT * FROM audit_history WHERE id = ?", (history_id,)
        ).fetchone()
        if row is None:
            return None
        session = dict(row)
        session["batch_result"] = json.loads(session["batch_result"])
        return session


# ==========================================
# SECTION 7: DELETE AUDIT HISTORY
# Purpose: Remove one saved audit session
# ==========================================

def delete_audit_history(history_id: int) -> bool:
    with sqlite3.connect(DATABASE_PATH) as connection:
        cursor = connection.execute(
            "DELETE FROM audit_history WHERE id = ?", (history_id,)
        )
        return cursor.rowcount > 0
