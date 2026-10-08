"""Small local SQLite audit log for hackathon demo runs."""
from pathlib import Path
import json
import sqlite3
from datetime import datetime, timezone

DB_PATH = Path(__file__).resolve().parents[1] / "outputs" / "trustlayer_audit.db"

def save_run(summary: dict, filename: str) -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as con:
        con.execute("""CREATE TABLE IF NOT EXISTS audit_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_at TEXT NOT NULL,
            filename TEXT NOT NULL,
            status TEXT NOT NULL,
            total_rows INTEGER NOT NULL,
            approved_rows INTEGER NOT NULL,
            quarantined_rows INTEGER NOT NULL,
            quality_score REAL NOT NULL,
            summary_json TEXT NOT NULL
        )""")
        con.execute("INSERT INTO audit_runs (run_at, filename, status, total_rows, approved_rows, quarantined_rows, quality_score, summary_json) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", (
            datetime.now(timezone.utc).isoformat(timespec="seconds"), filename,
            summary["batch_status"], summary["total_rows"], summary["approved_rows"],
            summary["quarantined_rows"], summary["data_quality_score"], json.dumps(summary),
        ))

def get_runs(limit: int = 50):
    if not DB_PATH.exists():
        return []
    with sqlite3.connect(DB_PATH) as con:
        con.row_factory = sqlite3.Row
        rows = con.execute("SELECT run_at, filename, status, total_rows, approved_rows, quarantined_rows, quality_score FROM audit_runs ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        return [dict(row) for row in rows]
