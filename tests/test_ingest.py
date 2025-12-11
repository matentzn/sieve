"""Tests for ingestion module."""

import pytest

from curation_app.db import CurationDatabase
from curation_app.ingest import parse_curation_record


@pytest.fixture
def db(tmp_path):
    db_path = tmp_path / "test.duckdb"
    return CurationDatabase(str(db_path))


def test_parse_minimal_record():
    data = {
        "id": "test-001",
        "assertion": {
            "subject_id": "MONDO:0001",
            "predicate": "rdfs:subClassOf",
            "object_id": "MONDO:0002",
        },
    }
    record = parse_curation_record(data)
    assert record.id == "test-001"
    assert record.assertion.subject_id == "MONDO:0001"
    assert record.status.value == "PENDING"


def test_parse_record_with_evidence():
    data = {
        "id": "test-002",
        "assertion": {
            "subject_id": "MONDO:0001",
            "subject_label": "disease A",
            "predicate": "rdfs:subClassOf",
            "object_id": "MONDO:0002",
            "object_label": "disease B",
        },
        "evidence_items": [
            {
                "id": "ev-001",
                "evidence_type": "LITERATURE",
                "publication_id": "PMID:12345",
                "quoted_text": "Test quote",
            }
        ],
    }
    record = parse_curation_record(data)
    assert record.id == "test-002"
    assert len(record.evidence_items) == 1
    assert record.evidence_items[0].evidence_type.value == "LITERATURE"
    assert record.evidence_items[0].publication_id == "PMID:12345"


def test_insert_and_retrieve(db):
    data = {
        "id": "test-003",
        "assertion": {
            "subject_id": "MONDO:0001",
            "predicate": "rdfs:subClassOf",
            "object_id": "MONDO:0002",
        },
    }
    record = parse_curation_record(data)
    db.insert_record(record)

    retrieved = db.get_record("test-003")
    assert retrieved is not None
    assert retrieved["assertion_subject_id"] == "MONDO:0001"


def test_record_exists(db):
    data = {
        "id": "test-004",
        "assertion": {
            "subject_id": "MONDO:0001",
            "predicate": "rdfs:subClassOf",
            "object_id": "MONDO:0002",
        },
    }
    record = parse_curation_record(data)

    assert not db.record_exists("test-004")
    db.insert_record(record)
    assert db.record_exists("test-004")


def test_get_records_by_status(db):
    for i in range(3):
        data = {
            "id": f"test-pending-{i}",
            "assertion": {
                "subject_id": f"MONDO:000{i}",
                "predicate": "rdfs:subClassOf",
                "object_id": "MONDO:9999",
            },
        }
        record = parse_curation_record(data)
        db.insert_record(record)

    pending = db.get_records_by_status("PENDING")
    assert len(pending) == 3


def test_stats(db):
    data = {
        "id": "test-stats-001",
        "assertion": {
            "subject_id": "MONDO:0001",
            "predicate": "rdfs:subClassOf",
            "object_id": "MONDO:0002",
        },
    }
    record = parse_curation_record(data)
    db.insert_record(record)

    stats = db.get_stats()
    assert stats["total"] == 1
    assert stats["pending"] == 1
    assert stats["accepted"] == 0
