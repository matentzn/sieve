"""DuckDB repository for curation records and decisions."""

import json
from datetime import datetime
from pathlib import Path
from typing import Optional

import duckdb

from sieve.models import CurationDecision, CurationRecord


class CurationDatabase:
    """DuckDB-backed storage for curation data."""

    def __init__(self, db_path: str = "data/curation.duckdb"):
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = duckdb.connect(db_path)
        self._init_schema()

    def _init_schema(self):
        """Create tables if they don't exist."""
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS curation_records (
                id VARCHAR PRIMARY KEY,
                assertion_subject_id VARCHAR NOT NULL,
                assertion_subject_label VARCHAR,
                assertion_predicate VARCHAR NOT NULL,
                assertion_predicate_label VARCHAR,
                assertion_object_id VARCHAR NOT NULL,
                assertion_object_label VARCHAR,
                provenance_attributed_to VARCHAR,
                provenance_attributed_to_label VARCHAR,
                provenance_generated_at DATE,
                provenance_source_version VARCHAR,
                provenance_source_uri VARCHAR,
                evidence_items JSON,
                source_artifact_uri VARCHAR,
                source_artifact_type VARCHAR,
                status VARCHAR NOT NULL DEFAULT 'PENDING',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS curation_decisions (
                id VARCHAR PRIMARY KEY,
                record_id VARCHAR NOT NULL,
                curator_orcid VARCHAR NOT NULL,
                curator_name VARCHAR,
                decision VARCHAR NOT NULL,
                rationale TEXT,
                decided_at TIMESTAMP NOT NULL,
                FOREIGN KEY (record_id) REFERENCES curation_records(id)
            )
        """)

    def insert_record(self, record: CurationRecord) -> str:
        """Insert a new curation record."""
        evidence_json = json.dumps(
            [
                e.model_dump(mode="json", exclude_none=True)
                for e in (record.evidence_items or [])
            ]
        )

        self.conn.execute(
            """
            INSERT INTO curation_records (
                id, assertion_subject_id, assertion_subject_label,
                assertion_predicate, assertion_predicate_label,
                assertion_object_id, assertion_object_label,
                provenance_attributed_to, provenance_attributed_to_label,
                provenance_generated_at, provenance_source_version, provenance_source_uri,
                evidence_items, source_artifact_uri, source_artifact_type,
                status, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            [
                record.id,
                record.assertion.subject_id,
                record.assertion.subject_label,
                record.assertion.predicate,
                record.assertion.predicate_label,
                record.assertion.object_id,
                record.assertion.object_label,
                record.provenance.attributed_to if record.provenance else None,
                record.provenance.attributed_to_label if record.provenance else None,
                record.provenance.generated_at if record.provenance else None,
                record.provenance.source_version if record.provenance else None,
                record.provenance.source_uri if record.provenance else None,
                evidence_json,
                record.source_artifact_uri,
                record.source_artifact_type,
                record.status.value if record.status else "PENDING",
                record.created_at or datetime.now(),
                record.updated_at or datetime.now(),
            ],
        )
        return record.id

    def get_record(self, record_id: str) -> Optional[dict]:
        """Get a single record by ID."""
        result = self.conn.execute(
            "SELECT * FROM curation_records WHERE id = ?", [record_id]
        ).fetchone()
        if result:
            return self._row_to_dict(result)
        return None

    def get_records_by_status(self, status: str) -> list[dict]:
        """Get all records with given status."""
        results = self.conn.execute(
            "SELECT * FROM curation_records WHERE status = ? ORDER BY created_at DESC",
            [status],
        ).fetchall()
        return [self._row_to_dict(r) for r in results]

    def get_all_records(self) -> list[dict]:
        """Get all records."""
        results = self.conn.execute(
            "SELECT * FROM curation_records ORDER BY created_at DESC"
        ).fetchall()
        return [self._row_to_dict(r) for r in results]

    def update_status(self, record_id: str, status: str):
        """Update record status."""
        self.conn.execute(
            "UPDATE curation_records SET status = ?, updated_at = ? WHERE id = ?",
            [status, datetime.now(), record_id],
        )

    def record_decision(self, decision: CurationDecision):
        """Record a curation decision and update record status."""
        self.conn.execute(
            """
            INSERT INTO curation_decisions (
                id, record_id, curator_orcid, curator_name,
                decision, rationale, decided_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
            [
                decision.id,
                decision.record_id,
                decision.curator_orcid,
                decision.curator_name,
                decision.decision.value if hasattr(decision.decision, "value") else decision.decision,
                decision.rationale,
                decision.decided_at,
            ],
        )

        # Map decision type to status
        status_map = {"ACCEPT": "ACCEPTED", "REJECT": "REJECTED", "DEFER": "DEFERRED"}
        decision_value = decision.decision.value if hasattr(decision.decision, "value") else decision.decision
        self.update_status(decision.record_id, status_map[decision_value])

    def get_decisions_for_record(self, record_id: str) -> list[dict]:
        """Get all decisions for a record."""
        results = self.conn.execute(
            "SELECT * FROM curation_decisions WHERE record_id = ? ORDER BY decided_at DESC",
            [record_id],
        ).fetchall()
        columns = [
            "id",
            "record_id",
            "curator_orcid",
            "curator_name",
            "decision",
            "rationale",
            "decided_at",
        ]
        return [dict(zip(columns, r)) for r in results]

    def get_stats(self) -> dict:
        """Get summary statistics."""
        result = self.conn.execute("""
            SELECT
                COUNT(*) as total,
                COALESCE(SUM(CASE WHEN status = 'PENDING' THEN 1 ELSE 0 END), 0) as pending,
                COALESCE(SUM(CASE WHEN status = 'ACCEPTED' THEN 1 ELSE 0 END), 0) as accepted,
                COALESCE(SUM(CASE WHEN status = 'REJECTED' THEN 1 ELSE 0 END), 0) as rejected,
                COALESCE(SUM(CASE WHEN status = 'DEFERRED' THEN 1 ELSE 0 END), 0) as deferred
            FROM curation_records
        """).fetchone()
        if result is None:
            return {
                "total": 0,
                "pending": 0,
                "accepted": 0,
                "rejected": 0,
                "deferred": 0,
            }
        return {
            "total": result[0] or 0,
            "pending": result[1] or 0,
            "accepted": result[2] or 0,
            "rejected": result[3] or 0,
            "deferred": result[4] or 0,
        }

    def _row_to_dict(self, row) -> dict:
        """Convert database row to dictionary."""
        columns = [
            "id",
            "assertion_subject_id",
            "assertion_subject_label",
            "assertion_predicate",
            "assertion_predicate_label",
            "assertion_object_id",
            "assertion_object_label",
            "provenance_attributed_to",
            "provenance_attributed_to_label",
            "provenance_generated_at",
            "provenance_source_version",
            "provenance_source_uri",
            "evidence_items",
            "source_artifact_uri",
            "source_artifact_type",
            "status",
            "created_at",
            "updated_at",
        ]
        d = dict(zip(columns, row))
        # Parse JSON evidence
        if d["evidence_items"]:
            if isinstance(d["evidence_items"], str):
                d["evidence_items"] = json.loads(d["evidence_items"])
        return d

    def record_exists(self, record_id: str) -> bool:
        """Check if a record with given ID exists."""
        result = self.conn.execute(
            "SELECT 1 FROM curation_records WHERE id = ?", [record_id]
        ).fetchone()
        return result is not None

    def close(self):
        """Close database connection."""
        self.conn.close()
