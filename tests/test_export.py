"""Tests for YAML export functionality."""

import io
import tarfile

import pytest
import yaml

from sieve.db import CurationDatabase
from sieve.export import (
    create_export_tarball,
    generate_export_records,
    record_to_export_dict,
    record_to_yaml,
)
from sieve.ingest import parse_curation_record
from sieve.models import CurationDecision, DecisionType


@pytest.fixture
def db(tmp_path):
    """Create a test database."""
    db_path = tmp_path / "test.duckdb"
    return CurationDatabase(str(db_path))


@pytest.fixture
def sample_record():
    """Create a sample record dict as it would come from the database."""
    return {
        "id": "test-record-001",
        "assertion_subject_id": "MONDO:0000005",
        "assertion_subject_label": "asthma",
        "assertion_predicate": "rdfs:subClassOf",
        "assertion_predicate_label": "subClassOf",
        "assertion_object_id": "MONDO:0100118",
        "assertion_object_label": "respiratory system disorder",
        "assertion_display_text": "asthma subClassOf respiratory system disorder",
        "status": "ACCEPTED",
        "evidence_steward": "orcid:0000-0001-2345-6789",
        "confidence": 0.85,
        "provenance": {
            "attributed_to": ["orcid:0000-0001-1234-5678"],
            "generated_at": "2024-01-15",
        },
        "evidence": [
            {
                "id": "ev-001",
                "evidence_type": "LITERATURE",
                "direction": "SUPPORTS",
                "evidence_strength": 0.9,
                "publication_id": "PMID:12345",
                "quoted_text": "Asthma is a respiratory disease.",
            }
        ],
    }


@pytest.fixture
def sample_decision():
    """Create a sample decision dict."""
    return {
        "id": "decision-001",
        "record_id": "test-record-001",
        "curator_orcid": "orcid:0000-0001-2345-6789",
        "curator_name": "Test Curator",
        "decision": "ACCEPT",
        "certainty": 0.85,
        "rationale": "Strong literature support",
        "decided_at": "2024-01-20T10:30:00",
    }


def test_record_to_export_dict_basic(sample_record):
    """Test basic record conversion to export dict."""
    export = record_to_export_dict(sample_record)

    assert export["id"] == "test-record-001"
    assert export["status"] == "ACCEPTED"
    assert export["assertion"]["subject_id"] == "MONDO:0000005"
    assert export["assertion"]["predicate"] == "rdfs:subClassOf"
    assert export["assertion"]["object_id"] == "MONDO:0100118"
    assert export["evidence_steward"] == "orcid:0000-0001-2345-6789"
    assert export["confidence"] == 0.85


def test_record_to_export_dict_slot_order(sample_record):
    """Test that export dict keys are in canonical order."""
    export = record_to_export_dict(sample_record)

    # Get the keys in order
    keys = list(export.keys())

    # Expected order: id, status, last_updated, evidence_steward, confidence, assertion, provenance, evidence
    # Note: last_updated may be missing if not set in sample_record
    expected_order = ["id", "status", "evidence_steward", "confidence", "assertion", "provenance", "evidence"]

    # Filter to only keys that exist in export
    actual_order = [k for k in keys]
    expected_filtered = [k for k in expected_order if k in export]

    assert actual_order == expected_filtered


def test_record_to_export_dict_with_decision(sample_record, sample_decision):
    """Test that decision is added as EXPERT_REVIEW evidence."""
    export = record_to_export_dict(sample_record, sample_decision)

    # Should have 2 evidence items - original + decision
    assert len(export["evidence"]) == 2

    # Find the decision evidence
    decision_ev = [e for e in export["evidence"] if e.get("id") == "decision-001"]
    assert len(decision_ev) == 1

    ev = decision_ev[0]
    assert ev["evidence_type"] == "EXPERT_REVIEW"
    assert ev["direction"] == "SUPPORTS"
    assert ev["evidence_strength"] == 0.85
    assert ev["reviewer_orcid"] == "orcid:0000-0001-2345-6789"
    assert "Strong literature support" in ev["description"]


def test_record_to_export_dict_rejected_decision(sample_record):
    """Test that REJECT decision has CONTRADICTS direction."""
    decision = {
        "id": "decision-002",
        "decision": "REJECT",
        "certainty": 0.9,
        "curator_orcid": "orcid:0000-0002-3456-7890",
    }

    export = record_to_export_dict(sample_record, decision)
    decision_ev = [e for e in export["evidence"] if e.get("id") == "decision-002"][0]

    assert decision_ev["direction"] == "CONTRADICTS"


def test_record_to_yaml_format(sample_record, sample_decision):
    """Test that YAML output is valid and parseable."""
    yaml_str = record_to_yaml(sample_record, sample_decision)

    # Should be valid YAML
    parsed = yaml.safe_load(yaml_str)

    assert parsed["id"] == "test-record-001"
    assert parsed["status"] == "ACCEPTED"
    assert "assertion" in parsed
    assert "evidence" in parsed


def test_generate_export_records(db):
    """Test generating export records from database."""
    from datetime import datetime

    # Create and insert a record
    data = {
        "id": "export-test-001",
        "assertion": {
            "subject_id": "MONDO:0001",
            "predicate": "rdfs:subClassOf",
            "object_id": "MONDO:0002",
        },
    }
    record = parse_curation_record(data)
    db.insert_record(record)

    # Make a decision to move it to ACCEPTED
    decision = CurationDecision(
        id="decision-export-001",
        record_id="export-test-001",
        curator_orcid="orcid:0000-0001-2345-6789",
        decision=DecisionType.ACCEPT,
        certainty=0.8,
        decided_at=datetime.now(),
    )
    db.record_decision(decision)

    # Generate exports
    exports = list(generate_export_records(db, statuses=["ACCEPTED"]))

    assert len(exports) == 1
    filename, yaml_content, status = exports[0]

    assert status == "ACCEPTED"
    assert filename.startswith("accepted/")
    assert filename.endswith(".yaml")

    # Verify YAML is valid
    parsed = yaml.safe_load(yaml_content)
    assert parsed["id"] == "export-test-001"
    assert parsed["status"] == "ACCEPTED"


def test_create_export_tarball(db):
    """Test creating a tar.gz archive of records."""
    from datetime import datetime

    # Create and accept a record
    data = {
        "id": "tarball-test-001",
        "assertion": {
            "subject_id": "MONDO:0001",
            "predicate": "rdfs:subClassOf",
            "object_id": "MONDO:0002",
        },
    }
    record = parse_curation_record(data)
    db.insert_record(record)

    decision = CurationDecision(
        id="decision-tarball-001",
        record_id="tarball-test-001",
        curator_orcid="orcid:0000-0001-2345-6789",
        decision=DecisionType.ACCEPT,
        certainty=0.9,
        decided_at=datetime.now(),
    )
    db.record_decision(decision)

    # Create tarball
    tarball_bytes = create_export_tarball(db)

    # Verify it's a valid tar.gz
    assert len(tarball_bytes) > 0

    buffer = io.BytesIO(tarball_bytes)
    with tarfile.open(fileobj=buffer, mode="r:gz") as tar:
        names = tar.getnames()
        assert len(names) == 1
        assert names[0].startswith("accepted/")
        assert names[0].endswith(".yaml")

        # Extract and verify content
        member = tar.getmember(names[0])
        f = tar.extractfile(member)
        content = f.read().decode("utf-8")
        parsed = yaml.safe_load(content)
        assert parsed["id"] == "tarball-test-001"


def test_create_export_tarball_multiple_statuses(db):
    """Test tarball with records of different statuses."""
    from datetime import datetime

    # Create accepted record
    data1 = {
        "id": "multi-test-001",
        "assertion": {
            "subject_id": "MONDO:0001",
            "predicate": "rdfs:subClassOf",
            "object_id": "MONDO:0002",
        },
    }
    db.insert_record(parse_curation_record(data1))
    db.record_decision(
        CurationDecision(
            id="dec-multi-001",
            record_id="multi-test-001",
            curator_orcid="orcid:0000-0001-2345-6789",
            decision=DecisionType.ACCEPT,
            certainty=0.9,
            decided_at=datetime.now(),
        )
    )

    # Create rejected record
    data2 = {
        "id": "multi-test-002",
        "assertion": {
            "subject_id": "MONDO:0003",
            "predicate": "rdfs:subClassOf",
            "object_id": "MONDO:0004",
        },
    }
    db.insert_record(parse_curation_record(data2))
    db.record_decision(
        CurationDecision(
            id="dec-multi-002",
            record_id="multi-test-002",
            curator_orcid="orcid:0000-0001-2345-6789",
            decision=DecisionType.REJECT,
            certainty=0.8,
            rationale="Insufficient evidence",
            decided_at=datetime.now(),
        )
    )

    # Create tarball
    tarball_bytes = create_export_tarball(db)

    buffer = io.BytesIO(tarball_bytes)
    with tarfile.open(fileobj=buffer, mode="r:gz") as tar:
        names = tar.getnames()
        assert len(names) == 2

        # Check we have both directories
        assert any(n.startswith("accepted/") for n in names)
        assert any(n.startswith("rejected/") for n in names)


def test_empty_export_tarball(db):
    """Test tarball creation with no reviewed records."""
    tarball_bytes = create_export_tarball(db)

    # Should still be valid (empty) tar.gz
    buffer = io.BytesIO(tarball_bytes)
    with tarfile.open(fileobj=buffer, mode="r:gz") as tar:
        names = tar.getnames()
        assert len(names) == 0


def test_record_to_export_dict_with_evidence_ratings():
    """Test that evidence ratings are included in export."""
    record = {
        "id": "test-ratings-export",
        "status": "ACCEPTED",
        "assertion_subject_id": "MONDO:0001",
        "assertion_predicate": "rdfs:subClassOf",
        "assertion_object_id": "MONDO:0002",
        "evidence": [
            {
                "id": "ev-001",
                "evidence_type": "LITERATURE",
                "rating": "ACCEPTED",
            },
            {
                "id": "ev-002",
                "evidence_type": "CONCORDANCE",
                "rating": "REJECTED",
            },
            {
                "id": "ev-003",
                "evidence_type": "COMPUTATIONAL",
                # No rating set
            },
        ],
    }

    export = record_to_export_dict(record)

    # Check ratings are preserved
    assert len(export["evidence"]) == 3
    assert export["evidence"][0]["rating"] == "ACCEPTED"
    assert export["evidence"][1]["rating"] == "REJECTED"
    assert export["evidence"][2].get("rating") is None
