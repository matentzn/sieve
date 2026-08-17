"""DuckDB store for SEPIO EvidencePackets and curation decisions."""

import json
from pathlib import Path
from typing import Any, Optional

import duckdb

from sieve.datamodel import CurationDecision, EvidencePacket
from sieve.datamodel.loaders import packet_from_dict
from sieve.scoring import net_evidence_ratio


class PacketStore:
    """DuckDB-backed storage for EvidencePackets (full JSON + promoted columns)."""

    def __init__(self, db_path: str = "data/sieve.duckdb"):
        self.db_path = db_path
        if db_path != ":memory:":
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = duckdb.connect(db_path)
        self._init_schema()

    def _init_schema(self) -> None:
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS evidence_packets (
                id VARCHAR PRIMARY KEY,
                subject_id VARCHAR,
                predicate VARCHAR,
                object_id VARCHAR,
                status VARCHAR,
                evidence_score DOUBLE,
                evidence_steward VARCHAR,
                created VARCHAR,
                updated VARCHAR,
                packet_json JSON
            )
        """)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS packet_decisions (
                id VARCHAR PRIMARY KEY,
                packet_id VARCHAR,
                curator VARCHAR,
                curator_name VARCHAR,
                decision VARCHAR,
                rationale VARCHAR,
                certainty DOUBLE,
                decided_at VARCHAR
            )
        """)

    @staticmethod
    def _steward(packet: EvidencePacket) -> Optional[str]:
        cb = packet.curated_by
        if cb and getattr(cb, "contributor", None):
            return getattr(cb.contributor, "id", None)
        return None

    def insert_packet(self, packet: EvidencePacket) -> str:
        stmt = packet.statement
        predicate = None
        if stmt and stmt.predicate:
            predicate = getattr(stmt.predicate, "code", None)
        self.conn.execute(
            """INSERT OR REPLACE INTO evidence_packets
               (id, subject_id, predicate, object_id, status, evidence_score,
                evidence_steward, created, updated, packet_json)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            [
                str(packet.id),
                getattr(stmt, "subject", None) if stmt else None,
                predicate,
                getattr(stmt, "object", None) if stmt else None,
                str(packet.status) if packet.status else "UNREVIEWED",
                net_evidence_ratio(packet),
                self._steward(packet),
                str(packet.created) if packet.created else None,
                str(packet.updated) if packet.updated else None,
                # serialize_as_any so polymorphic evidence items keep their
                # subclass fields (otherwise they collapse to id+type).
                packet.model_dump_json(exclude_none=True, serialize_as_any=True),
            ],
        )
        return str(packet.id)

    def get_packet(self, packet_id: str) -> Optional[EvidencePacket]:
        row = self.conn.execute(
            "SELECT packet_json FROM evidence_packets WHERE id = ?", [packet_id]
        ).fetchone()
        if not row:
            return None
        return packet_from_dict(json.loads(row[0]))

    def list_packets(self, status: Optional[str] = None) -> list[dict[str, Any]]:
        cols = ["id", "subject_id", "predicate", "object_id", "status", "evidence_score"]
        select = f"SELECT {', '.join(cols)} FROM evidence_packets"
        if status:
            rows = self.conn.execute(f"{select} WHERE status = ? ORDER BY id", [status]).fetchall()
        else:
            rows = self.conn.execute(f"{select} ORDER BY id").fetchall()
        return [dict(zip(cols, r)) for r in rows]

    def get_stats(self) -> dict[str, int]:
        rows = self.conn.execute(
            "SELECT status, COUNT(*) FROM evidence_packets GROUP BY status"
        ).fetchall()
        return {str(status): int(count) for status, count in rows}

    def update_status(self, packet_id: str, status: str) -> None:
        """Set a packet's status (in the promoted column and the stored JSON)."""
        packet = self.get_packet(packet_id)
        if packet is None:
            return
        packet.status = status  # type: ignore[assignment]
        self.insert_packet(packet)

    def set_item_rating(self, packet_id: str, item_id: str, rating: str) -> None:
        """Set the steward's rating on a single evidence item, by item id."""
        packet = self.get_packet(packet_id)
        if packet is None:
            return
        for line in packet.has_evidence_lines or []:
            for item in line.has_evidence_items or []:
                if getattr(item, "id", None) == item_id:
                    item.rating = rating  # type: ignore[attr-defined]
        self.insert_packet(packet)

    def get_decisions(self, packet_id: str) -> list[dict[str, Any]]:
        """Return the decision history for a packet, newest first."""
        cols = ["id", "packet_id", "curator", "curator_name", "decision",
                "rationale", "certainty", "decided_at"]
        rows = self.conn.execute(
            f"SELECT {', '.join(cols)} FROM packet_decisions "
            "WHERE packet_id = ? ORDER BY decided_at DESC",
            [packet_id],
        ).fetchall()
        return [dict(zip(cols, r)) for r in rows]

    def record_decision(self, decision: CurationDecision) -> str:
        self.conn.execute(
            """INSERT OR REPLACE INTO packet_decisions
               (id, packet_id, curator, curator_name, decision, rationale, certainty, decided_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            [
                decision.id,
                str(decision.packet_id),
                str(decision.curator),
                decision.curator_name,
                str(decision.decision),
                decision.rationale,
                decision.certainty,
                str(decision.decided_at),
            ],
        )
        return decision.id

    def close(self) -> None:
        self.conn.close()
