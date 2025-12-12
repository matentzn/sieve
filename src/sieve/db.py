"""DuckDB repository for curation records and decisions."""

import json
from datetime import datetime
from pathlib import Path
from typing import Optional

import duckdb

from sieve.models import CurationDecision, CurationRecord


def calculate_evidence_score(evidence: list[dict]) -> float:
    """Calculate Net Evidence Ratio from evidence items.

    Formula: NER = (S+ - S-) / (S+ + S- + S?)
    Where:
    - S+ = sum of evidence_strength for SUPPORTS items
    - S- = sum of evidence_strength for CONTRADICTS items
    - S? = sum of evidence_strength for UNCERTAIN items

    Returns score from -1 (all contradicting) to +1 (all supporting)
    """
    if not evidence:
        return 0.0

    s_plus = 0.0
    s_minus = 0.0
    s_uncertain = 0.0

    for ev in evidence:
        strength = ev.get("evidence_strength", 1.0)
        direction = ev.get("direction", "SUPPORTS")

        if direction == "SUPPORTS":
            s_plus += strength
        elif direction == "CONTRADICTS":
            s_minus += strength
        else:
            s_uncertain += strength

    total = s_plus + s_minus + s_uncertain
    if total == 0:
        return 0.0

    return (s_plus - s_minus) / total


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
                last_updated DATE,
                assertion_subject_id VARCHAR NOT NULL,
                assertion_subject_label VARCHAR,
                assertion_predicate VARCHAR NOT NULL,
                assertion_predicate_label VARCHAR,
                assertion_object_id VARCHAR NOT NULL,
                assertion_object_label VARCHAR,
                assertion_display_text VARCHAR,
                provenance JSON,
                evidence JSON,
                evidence_score DOUBLE,
                status VARCHAR NOT NULL DEFAULT 'UNREVIEWED',
                evidence_steward VARCHAR,
                confidence DOUBLE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Add evidence_score column if it doesn't exist (migration)
        try:
            self.conn.execute(
                "ALTER TABLE curation_records ADD COLUMN evidence_score DOUBLE"
            )
        except duckdb.CatalogException:
            pass  # Column already exists

        # Add evidence_steward column if it doesn't exist (migration)
        try:
            self.conn.execute(
                "ALTER TABLE curation_records ADD COLUMN evidence_steward VARCHAR"
            )
        except duckdb.CatalogException:
            pass  # Column already exists

        # Add confidence column if it doesn't exist (migration)
        try:
            self.conn.execute(
                "ALTER TABLE curation_records ADD COLUMN confidence DOUBLE"
            )
        except duckdb.CatalogException:
            pass  # Column already exists

        # Migrate old status values to new ones
        self.conn.execute(
            "UPDATE curation_records SET status = 'UNREVIEWED' WHERE status = 'PENDING'"
        )
        self.conn.execute(
            "UPDATE curation_records SET status = 'CONTROVERSIAL' WHERE status = 'DEFERRED'"
        )

        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS curation_decisions (
                id VARCHAR PRIMARY KEY,
                record_id VARCHAR NOT NULL,
                curator_orcid VARCHAR NOT NULL,
                curator_name VARCHAR,
                decision VARCHAR NOT NULL,
                certainty DOUBLE DEFAULT 1.0,
                rationale TEXT,
                decided_at TIMESTAMP NOT NULL,
                FOREIGN KEY (record_id) REFERENCES curation_records(id)
            )
        """)

        # Add certainty column if it doesn't exist (migration)
        try:
            self.conn.execute(
                "ALTER TABLE curation_decisions ADD COLUMN certainty DOUBLE DEFAULT 1.0"
            )
        except duckdb.CatalogException:
            pass  # Column already exists

    def insert_record(self, record: CurationRecord) -> str:
        """Insert a new curation record."""
        evidence_list = [
            e.model_dump(mode="json", exclude_none=True)
            for e in (record.evidence or [])
        ]
        evidence_json = json.dumps(evidence_list)

        # Calculate and cache evidence score
        evidence_score = calculate_evidence_score(evidence_list)

        provenance_json = (
            json.dumps(record.provenance.model_dump(mode="json", exclude_none=True))
            if record.provenance
            else None
        )

        self.conn.execute(
            """
            INSERT INTO curation_records (
                id, last_updated, assertion_subject_id, assertion_subject_label,
                assertion_predicate, assertion_predicate_label,
                assertion_object_id, assertion_object_label, assertion_display_text,
                provenance, evidence, evidence_score, status,
                evidence_steward, confidence, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            [
                record.id,
                record.last_updated,
                record.assertion.subject_id,
                record.assertion.subject_label,
                record.assertion.predicate,
                record.assertion.predicate_label,
                record.assertion.object_id,
                record.assertion.object_label,
                record.assertion.display_text,
                provenance_json,
                evidence_json,
                evidence_score,
                record.status.value if record.status else "UNREVIEWED",
                record.evidence_steward,
                record.confidence,
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

    def get_records_paginated(
        self,
        status: Optional[str] = None,
        offset: int = 0,
        limit: int = 50,
        sort_by: str = "created_at",
        sort_order: str = "DESC",
    ) -> tuple[list[dict], int]:
        """Get paginated records with sorting.

        Returns tuple of (records, total_count).
        Only fetches columns needed for table display (not full evidence JSON).
        """
        # Validate sort column to prevent SQL injection
        valid_sort_columns = {
            "created_at",
            "evidence_score",
            "assertion_display_text",
            "assertion_predicate",
        }
        if sort_by not in valid_sort_columns:
            sort_by = "created_at"
        if sort_order.upper() not in ("ASC", "DESC"):
            sort_order = "DESC"

        # Build WHERE clause
        where_clause = ""
        params = []
        if status:
            where_clause = "WHERE status = ?"
            params.append(status)

        # Get total count
        count_query = f"SELECT COUNT(*) FROM curation_records {where_clause}"
        total_count = self.conn.execute(count_query, params).fetchone()[0]

        # Get paginated results (lightweight columns only for table)
        query = f"""
            SELECT
                id,
                assertion_display_text,
                assertion_subject_label,
                assertion_subject_id,
                assertion_predicate_label,
                assertion_predicate,
                assertion_object_label,
                assertion_object_id,
                evidence_score,
                status,
                created_at
            FROM curation_records
            {where_clause}
            ORDER BY {sort_by} {sort_order}
            LIMIT ? OFFSET ?
        """
        params.extend([limit, offset])
        results = self.conn.execute(query, params).fetchall()

        columns = [
            "id",
            "assertion_display_text",
            "assertion_subject_label",
            "assertion_subject_id",
            "assertion_predicate_label",
            "assertion_predicate",
            "assertion_object_label",
            "assertion_object_id",
            "evidence_score",
            "status",
            "created_at",
        ]
        records = [dict(zip(columns, r)) for r in results]

        return records, total_count

    def get_records_with_decisions_paginated(
        self,
        status: str,
        offset: int = 0,
        limit: int = 50,
        sort_by: str = "decided_at",
        sort_order: str = "DESC",
    ) -> tuple[list[dict], int]:
        """Get paginated records with decision info for a given status.

        Returns tuple of (records, total_count).
        Includes curator info from the most recent decision.
        """
        # Validate sort column to prevent SQL injection
        valid_sort_columns = {
            "decided_at",
            "evidence_score",
            "assertion_display_text",
            "curator_name",
            "certainty",
        }
        if sort_by not in valid_sort_columns:
            sort_by = "decided_at"
        if sort_order.upper() not in ("ASC", "DESC"):
            sort_order = "DESC"

        # Get total count
        count_query = "SELECT COUNT(*) FROM curation_records WHERE status = ?"
        total_count = self.conn.execute(count_query, [status]).fetchone()[0]

        # Get paginated results with latest decision info
        # Using a subquery to get the most recent decision for each record
        query = f"""
            SELECT
                r.id,
                r.assertion_display_text,
                r.assertion_subject_label,
                r.assertion_subject_id,
                r.assertion_predicate_label,
                r.assertion_predicate,
                r.assertion_object_label,
                r.assertion_object_id,
                r.evidence_score,
                r.status,
                r.created_at,
                d.curator_orcid,
                d.curator_name,
                d.decided_at,
                d.certainty,
                d.rationale
            FROM curation_records r
            LEFT JOIN (
                SELECT record_id, curator_orcid, curator_name, decided_at, certainty, rationale,
                       ROW_NUMBER() OVER (PARTITION BY record_id ORDER BY decided_at DESC) as rn
                FROM curation_decisions
            ) d ON r.id = d.record_id AND d.rn = 1
            WHERE r.status = ?
            ORDER BY {sort_by} {sort_order}
            LIMIT ? OFFSET ?
        """
        results = self.conn.execute(query, [status, limit, offset]).fetchall()

        columns = [
            "id",
            "assertion_display_text",
            "assertion_subject_label",
            "assertion_subject_id",
            "assertion_predicate_label",
            "assertion_predicate",
            "assertion_object_label",
            "assertion_object_id",
            "evidence_score",
            "status",
            "created_at",
            "curator_orcid",
            "curator_name",
            "decided_at",
            "certainty",
            "rationale",
        ]
        records = [dict(zip(columns, r)) for r in results]

        return records, total_count

    def return_to_queue(self, record_id: str):
        """Return a record to UNREVIEWED status (for admin use)."""
        self.conn.execute(
            """UPDATE curation_records
               SET status = 'UNREVIEWED', evidence_steward = NULL, confidence = NULL, updated_at = ?
               WHERE id = ?""",
            [datetime.now(), record_id],
        )

    def get_all_records(self) -> list[dict]:
        """Get all records."""
        results = self.conn.execute(
            "SELECT * FROM curation_records ORDER BY created_at DESC"
        ).fetchall()
        return [self._row_to_dict(r) for r in results]

    def update_status(
        self,
        record_id: str,
        status: str,
        evidence_steward: str | None = None,
        confidence: float | None = None,
    ):
        """Update record status, evidence_steward, and confidence."""
        self.conn.execute(
            """UPDATE curation_records
               SET status = ?, evidence_steward = ?, confidence = ?, updated_at = ?
               WHERE id = ?""",
            [status, evidence_steward, confidence, datetime.now(), record_id],
        )

    def record_decision(self, decision: CurationDecision):
        """Record a curation decision and update record status."""
        self.conn.execute(
            """
            INSERT INTO curation_decisions (
                id, record_id, curator_orcid, curator_name,
                decision, certainty, rationale, decided_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
            [
                decision.id,
                decision.record_id,
                decision.curator_orcid,
                decision.curator_name,
                decision.decision.value if hasattr(decision.decision, "value") else decision.decision,
                decision.certainty,
                decision.rationale,
                decision.decided_at,
            ],
        )

        # Map decision type to status
        status_map = {"ACCEPT": "ACCEPTED", "REJECT": "REJECTED", "CONTROVERSIAL": "CONTROVERSIAL"}
        decision_value = decision.decision.value if hasattr(decision.decision, "value") else decision.decision
        self.update_status(
            decision.record_id,
            status_map[decision_value],
            evidence_steward=decision.curator_orcid,
            confidence=decision.certainty,
        )

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
            "certainty",
            "rationale",
            "decided_at",
        ]
        return [dict(zip(columns, r)) for r in results]

    def get_stats(self) -> dict:
        """Get summary statistics."""
        result = self.conn.execute("""
            SELECT
                COUNT(*) as total,
                COALESCE(SUM(CASE WHEN status = 'UNREVIEWED' THEN 1 ELSE 0 END), 0) as unreviewed,
                COALESCE(SUM(CASE WHEN status = 'ACCEPTED' THEN 1 ELSE 0 END), 0) as accepted,
                COALESCE(SUM(CASE WHEN status = 'REJECTED' THEN 1 ELSE 0 END), 0) as rejected,
                COALESCE(SUM(CASE WHEN status = 'CONTROVERSIAL' THEN 1 ELSE 0 END), 0) as controversial
            FROM curation_records
        """).fetchone()
        if result is None:
            return {
                "total": 0,
                "unreviewed": 0,
                "accepted": 0,
                "rejected": 0,
                "controversial": 0,
            }
        return {
            "total": result[0] or 0,
            "unreviewed": result[1] or 0,
            "accepted": result[2] or 0,
            "rejected": result[3] or 0,
            "controversial": result[4] or 0,
        }

    def _row_to_dict(self, row) -> dict:
        """Convert database row to dictionary."""
        columns = [
            "id",
            "last_updated",
            "assertion_subject_id",
            "assertion_subject_label",
            "assertion_predicate",
            "assertion_predicate_label",
            "assertion_object_id",
            "assertion_object_label",
            "assertion_display_text",
            "provenance",
            "evidence",
            "evidence_score",
            "status",
            "evidence_steward",
            "confidence",
            "created_at",
            "updated_at",
        ]
        d = dict(zip(columns, row))
        # Parse JSON fields
        if d["evidence"]:
            if isinstance(d["evidence"], str):
                d["evidence"] = json.loads(d["evidence"])
        if d["provenance"]:
            if isinstance(d["provenance"], str):
                d["provenance"] = json.loads(d["provenance"])
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
