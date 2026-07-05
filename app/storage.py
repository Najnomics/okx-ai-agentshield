import json
import sqlite3
from pathlib import Path
from typing import Any


class AuditStore:
    def __init__(self, data_dir: str) -> None:
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = self.data_dir / "agentshield.sqlite3"
        self._init()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS risk_checks (
                    audit_id TEXT PRIMARY KEY,
                    tool TEXT NOT NULL,
                    decision TEXT NOT NULL,
                    risk_score INTEGER NOT NULL,
                    confidence REAL NOT NULL,
                    input_hash TEXT NOT NULL,
                    evidence_hash TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

    def insert(self, record: dict[str, Any]) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO risk_checks (
                    audit_id, tool, decision, risk_score, confidence,
                    input_hash, evidence_hash, payload_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record["audit_id"],
                    record["tool"],
                    record["decision"],
                    record["risk_score"],
                    record["confidence"],
                    record["input_hash"],
                    record["evidence_hash"],
                    json.dumps(record, sort_keys=True),
                ),
            )

    def list_recent(self, limit: int = 50) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT payload_json, created_at FROM risk_checks ORDER BY created_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        records: list[dict[str, Any]] = []
        for row in rows:
            item = json.loads(row["payload_json"])
            item["created_at"] = row["created_at"]
            records.append(item)
        return records

