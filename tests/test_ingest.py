"""Tests for ingestion module."""

import pytest
from pydantic import ValidationError

from sieve.db import CurationDatabase
from sieve.ingest import parse_curation_record
from sieve.models import EvidenceSynthesis


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
    assert record.status.value == "UNREVIEWED"


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
        "evidence": [
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
    assert len(record.evidence) == 1
    assert record.evidence[0].evidence_type.value == "LITERATURE"
    assert record.evidence[0].publication_id == "PMID:12345"


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
            "id": f"test-unreviewed-{i}",
            "assertion": {
                "subject_id": f"MONDO:000{i}",
                "predicate": "rdfs:subClassOf",
                "object_id": "MONDO:9999",
            },
        }
        record = parse_curation_record(data)
        db.insert_record(record)

    unreviewed = db.get_records_by_status("UNREVIEWED")
    assert len(unreviewed) == 3


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
    assert stats["unreviewed"] == 1
    assert stats["accepted"] == 0


def test_record_decision_with_certainty(db):
    """Test that decisions can include certainty values."""
    from datetime import datetime

    from sieve.models import CurationDecision, DecisionType

    # Create a record
    data = {
        "id": "test-certainty-001",
        "assertion": {
            "subject_id": "MONDO:0001",
            "predicate": "rdfs:subClassOf",
            "object_id": "MONDO:0002",
        },
    }
    record = parse_curation_record(data)
    db.insert_record(record)

    # Make a decision with certainty
    decision = CurationDecision(
        id="decision-001",
        record_id="test-certainty-001",
        curator_orcid="orcid:0000-0001-2345-6789",
        curator_name="Test Curator",
        decision=DecisionType.ACCEPT,
        certainty=0.75,
        rationale="Test rationale",
        decided_at=datetime.now(),
    )
    db.record_decision(decision)

    # Retrieve and verify
    decisions = db.get_decisions_for_record("test-certainty-001")
    assert len(decisions) == 1
    assert decisions[0]["certainty"] == 0.75
    assert decisions[0]["decision"] == "ACCEPT"


def test_record_decision_default_certainty(db):
    """Test that decisions default to certainty of 1.0."""
    from datetime import datetime

    from sieve.models import CurationDecision, DecisionType

    # Create a record
    data = {
        "id": "test-default-certainty-001",
        "assertion": {
            "subject_id": "MONDO:0001",
            "predicate": "rdfs:subClassOf",
            "object_id": "MONDO:0002",
        },
    }
    record = parse_curation_record(data)
    db.insert_record(record)

    # Make a decision without specifying certainty
    decision = CurationDecision(
        id="decision-002",
        record_id="test-default-certainty-001",
        curator_orcid="orcid:0000-0001-2345-6789",
        curator_name="Test Curator",
        decision=DecisionType.REJECT,
        rationale="Test rejection",
        decided_at=datetime.now(),
    )
    db.record_decision(decision)

    # Retrieve and verify default certainty
    decisions = db.get_decisions_for_record("test-default-certainty-001")
    assert len(decisions) == 1
    assert decisions[0]["certainty"] == 1.0


def test_get_records_with_decisions_paginated_includes_certainty(db):
    """Test that paginated records include certainty from decisions."""
    from datetime import datetime

    from sieve.models import CurationDecision, DecisionType

    # Create a record
    data = {
        "id": "test-paginated-certainty-001",
        "assertion": {
            "subject_id": "MONDO:0001",
            "predicate": "rdfs:subClassOf",
            "object_id": "MONDO:0002",
        },
    }
    record = parse_curation_record(data)
    db.insert_record(record)

    # Make a decision with specific certainty
    decision = CurationDecision(
        id="decision-003",
        record_id="test-paginated-certainty-001",
        curator_orcid="orcid:0000-0001-2345-6789",
        curator_name="Test Curator",
        decision=DecisionType.ACCEPT,
        certainty=0.5,
        rationale=None,
        decided_at=datetime.now(),
    )
    db.record_decision(decision)

    # Retrieve paginated records
    records, total = db.get_records_with_decisions_paginated(
        status="ACCEPTED", offset=0, limit=10
    )
    assert total == 1
    assert len(records) == 1
    assert records[0]["certainty"] == 0.5


def test_certainty_validation():
    """Test that certainty must be between 0 and 1."""
    from datetime import datetime

    import pytest
    from pydantic import ValidationError

    from sieve.models import CurationDecision, DecisionType

    # Valid certainty values
    for valid_certainty in [0.0, 0.5, 1.0]:
        decision = CurationDecision(
            id="test-valid",
            record_id="record-001",
            curator_orcid="orcid:0000-0001-2345-6789",
            decision=DecisionType.ACCEPT,
            certainty=valid_certainty,
            decided_at=datetime.now(),
        )
        assert decision.certainty == valid_certainty

    # Invalid certainty values
    for invalid_certainty in [-0.1, 1.1, 2.0]:
        with pytest.raises(ValidationError):
            CurationDecision(
                id="test-invalid",
                record_id="record-001",
                curator_orcid="orcid:0000-0001-2345-6789",
                decision=DecisionType.ACCEPT,
                certainty=invalid_certainty,
                decided_at=datetime.now(),
            )


def test_record_decision_sets_evidence_steward_and_confidence(db):
    """Test that making a decision sets evidence_steward and confidence on the record."""
    from datetime import datetime

    from sieve.models import CurationDecision, DecisionType

    # Create a record
    data = {
        "id": "test-steward-001",
        "assertion": {
            "subject_id": "MONDO:0001",
            "predicate": "rdfs:subClassOf",
            "object_id": "MONDO:0002",
        },
    }
    record = parse_curation_record(data)
    db.insert_record(record)

    # Verify initial state - no steward or confidence
    initial_record = db.get_record("test-steward-001")
    assert initial_record["evidence_steward"] is None
    assert initial_record["confidence"] is None

    # Make a decision
    decision = CurationDecision(
        id="decision-steward-001",
        record_id="test-steward-001",
        curator_orcid="orcid:0000-0001-2345-6789",
        curator_name="Test Curator",
        decision=DecisionType.ACCEPT,
        certainty=0.85,
        rationale="Test rationale",
        decided_at=datetime.now(),
    )
    db.record_decision(decision)

    # Verify the record now has evidence_steward and confidence set
    updated_record = db.get_record("test-steward-001")
    assert updated_record["status"] == "ACCEPTED"
    assert updated_record["evidence_steward"] == "orcid:0000-0001-2345-6789"
    assert updated_record["confidence"] == 0.85


def test_return_to_queue_clears_steward_and_confidence(db):
    """Test that returning a record to queue clears evidence_steward and confidence."""
    from datetime import datetime

    from sieve.models import CurationDecision, DecisionType

    # Create and decide on a record
    data = {
        "id": "test-return-001",
        "assertion": {
            "subject_id": "MONDO:0001",
            "predicate": "rdfs:subClassOf",
            "object_id": "MONDO:0002",
        },
    }
    record = parse_curation_record(data)
    db.insert_record(record)

    decision = CurationDecision(
        id="decision-return-001",
        record_id="test-return-001",
        curator_orcid="orcid:0000-0001-2345-6789",
        decision=DecisionType.REJECT,
        certainty=0.9,
        decided_at=datetime.now(),
    )
    db.record_decision(decision)

    # Verify decision was recorded
    decided_record = db.get_record("test-return-001")
    assert decided_record["status"] == "REJECTED"
    assert decided_record["evidence_steward"] == "orcid:0000-0001-2345-6789"
    assert decided_record["confidence"] == 0.9

    # Return to queue
    db.return_to_queue("test-return-001")

    # Verify steward and confidence are cleared
    returned_record = db.get_record("test-return-001")
    assert returned_record["status"] == "UNREVIEWED"
    assert returned_record["evidence_steward"] is None
    assert returned_record["confidence"] is None


def test_evidence_synthesis_model():
    """Test that EvidenceSynthesis model can be created with required fields."""
    synthesis = EvidenceSynthesis(
        summary="Based on multiple concordance sources and literature evidence, "
        "the assertion is well-supported.",
        confidence=0.85,
    )
    assert synthesis.summary == (
        "Based on multiple concordance sources and literature evidence, "
        "the assertion is well-supported."
    )
    assert synthesis.confidence == 0.85


def test_evidence_synthesis_confidence_validation():
    """Test that confidence must be between 0 and 1."""
    # Valid values
    for valid_confidence in [0.0, 0.5, 1.0]:
        synthesis = EvidenceSynthesis(
            summary="Test summary",
            confidence=valid_confidence,
        )
        assert synthesis.confidence == valid_confidence

    # Invalid values
    for invalid_confidence in [-0.1, 1.1, 2.0]:
        with pytest.raises(ValidationError):
            EvidenceSynthesis(
                summary="Test summary",
                confidence=invalid_confidence,
            )


def test_evidence_synthesis_creation():
    """Test that EvidenceSynthesis can be created with required fields."""
    synthesis = EvidenceSynthesis(
        summary="The evidence strongly supports this assertion.",
        confidence=0.95,
    )
    assert synthesis.summary == "The evidence strongly supports this assertion."
    assert synthesis.confidence == 0.95


def test_evidence_synthesis_missing_required_fields():
    """Test that EvidenceSynthesis raises error when required fields are missing."""
    # Missing summary
    with pytest.raises(ValidationError):
        EvidenceSynthesis(confidence=0.5)

    # Missing confidence
    with pytest.raises(ValidationError):
        EvidenceSynthesis(summary="Test summary")

    # Both missing
    with pytest.raises(ValidationError):
        EvidenceSynthesis()


def test_parse_record_with_evidence_synthesis():
    """Test that curation records can include evidence synthesis."""
    data = {
        "id": "test-synthesis-001",
        "assertion": {
            "subject_id": "MONDO:0001",
            "predicate": "rdfs:subClassOf",
            "object_id": "MONDO:0002",
        },
        "evidence_synthesis": {
            "summary": "Strong concordance across multiple ontologies.",
            "confidence": 0.9,
        },
    }
    record = parse_curation_record(data)
    assert record.id == "test-synthesis-001"
    assert record.evidence_synthesis is not None
    assert record.evidence_synthesis.summary == "Strong concordance across multiple ontologies."
    assert record.evidence_synthesis.confidence == 0.9


def test_parse_record_with_evidence_synthesis_confidence_clamping():
    """Test that confidence values are clamped to [0.0, 1.0] range."""
    # Test value above 1.0 is clamped
    data = {
        "id": "test-clamp-high",
        "assertion": {
            "subject_id": "MONDO:0001",
            "predicate": "rdfs:subClassOf",
            "object_id": "MONDO:0002",
        },
        "evidence_synthesis": {
            "summary": "Test summary",
            "confidence": 1.5,
        },
    }
    record = parse_curation_record(data)
    assert record.evidence_synthesis.confidence == 1.0

    # Test value below 0.0 is clamped
    data["id"] = "test-clamp-low"
    data["evidence_synthesis"]["confidence"] = -0.5
    record = parse_curation_record(data)
    assert record.evidence_synthesis.confidence == 0.0
