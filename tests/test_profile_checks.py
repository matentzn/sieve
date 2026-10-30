"""Profile constraints that LinkML validation cannot express (sieve.profile_checks)."""

from pathlib import Path

import pytest

from sieve.profile_checks import check_packet
from tests.test_profile_examples import _load

VALID = sorted((Path(__file__).parent / "data" / "profile" / "valid").glob("*.yaml"))
DATA = Path(__file__).parent / "data" / "profile" / "valid"


def _codes(packet: dict, severity: str | None = None) -> set[str]:
    return {i.code for i in check_packet(packet) if severity is None or i.severity == severity}


@pytest.mark.parametrize("path", VALID, ids=lambda p: p.stem)
def test_examples_pass_profile_checks(path):
    assert _codes(_load(path), "ERROR") == set()


@pytest.fixture
def c005() -> dict:
    return _load(DATA / "c005_down_syndrome_not_hereditary.yaml")


@pytest.fixture
def c007() -> dict:
    return _load(DATA / "c007_cf_cftr_panel.yaml")


@pytest.fixture
def c006() -> dict:
    return _load(DATA / "c006_down_syndrome_icd10cm_batch.yaml")


def test_predicate_must_come_from_claim_type_value_set(c007):
    """C007 / RCS.STRUCTURED_STATEMENT: predicates are bound per claim type."""
    c007["statement"]["predicate"] = {"code": "skos:exactMatch"}
    assert "PREDICATE_BINDING" in _codes(c007, "ERROR")


def test_evidence_type_must_be_permitted_for_claim_type(c005):
    """MATRIX.C005: text passages are not evidence for a negative subclass claim."""
    c005["textPassages"] = [
        {"id": "sieve:tp/x", "type": "TextPassage", "statementText": "x", "reportedIn": ["PMID:1"]}
    ]
    c005["statement"]["hasEvidenceLines"][0]["hasEvidenceItems"] = ["sieve:tp/x"]
    assert "EVIDENCE_NOT_PERMITTED" in _codes(c005, "ERROR")


def test_dangling_evidence_reference(c005):
    c005["statement"]["hasEvidenceLines"][0]["hasEvidenceItems"] = ["DOID:999999"]
    assert "DANGLING_REFERENCE" in _codes(c005, "ERROR")


def test_higher_order_line_may_reference_a_line(c005):
    """EINT.STACKING: a line can interpret other lines."""
    lines = c005["statement"]["hasEvidenceLines"]
    lines.append({**lines[1], "id": "sieve:el/stack", "hasEvidenceItems": [lines[0]["id"], lines[1]["id"]]})
    assert _codes(c005, "ERROR") == set()


def test_negative_subclass_must_be_negated(c005):
    """C005 / D-032."""
    c005["statement"]["negated"] = False
    assert "NEGATION" in _codes(c005, "ERROR")


def test_plain_subclass_must_not_be_negated(c005):
    c005["statement"]["type"] = "SubclassStatement"
    assert "NEGATION" in _codes(c005, "ERROR")


def test_supporting_concordance_on_negative_claim_warns(c005):
    """MATRIX.C005 / D-033: a source asserting the positive subclass disputes."""
    c005["statement"]["hasEvidenceLines"][0]["directionOfEvidenceProvided"] = "supports"
    assert "CONCORDANCE_DIRECTION" in _codes(c005, "WARNING")


def test_preferred_only_on_exact_match(c006):
    """C006 / D-012."""
    c006["statement"]["predicate"] = {"code": "skos:broadMatch"}
    assert "PREFERRED_NOT_EXACT" in _codes(c006, "ERROR")


def test_obsolete_object_mapping_needs_review(c006):
    """C006 / D-011: obsolete subject + obsolete object is a WARNING state.

    Subject obsolescence is not stored on the mapping (D-009); the caller supplies it
    from the terms' existence claims.
    """
    c006["statement"]["objectObsoleteInSourceVersion"] = "2026"
    assert "OBSOLETE_TO_OBSOLETE" not in _codes(c006)
    issues = check_packet(c006, obsolete_terms={"MONDO:0008608"})
    assert any(i.code == "OBSOLETE_TO_OBSOLETE" and i.severity == "WARNING" for i in issues)


def test_definition_without_any_source_warns():
    """C002 / D-029."""
    packet = {
        "id": "sieve:pkt/def",
        "type": "EvidencePacket",
        "version": "1",
        "statement": {
            "id": "sieve:st/def",
            "type": "DefinitionStatement",
            "subject": "MONDO:1",
            "predicate": {"code": "IAO:0000115"},
            "object": "A disease.",
            "reviewState": "NOT_VERIFIED",
        },
    }
    assert "DEFINITION_WITHOUT_SOURCE" in _codes(packet, "WARNING")
    assert _codes(packet, "ERROR") == set()


def test_document_based_line_needs_read_coverage(c007):
    """D-059: what was read, and whether it was paywalled, is mandatory."""
    del c007["statement"]["hasEvidenceLines"][1]["contributions"][0]["accessStatus"]
    assert "READ_COVERAGE" in _codes(c007, "ERROR")


def test_ai_line_needs_its_workflow(c007):
    """PROV.INTERP.METHODS / D-050: AI lines name their workflow / prompt version."""
    del c007["statement"]["hasEvidenceLines"][1]["contributions"][0]["specifiedBy"]
    assert "METHOD_REQUIRED" in _codes(c007, "ERROR")


def test_rule_based_line_needs_its_rule(c007):
    del c007["statement"]["hasEvidenceLines"][0]["computedByRule"]
    assert "METHOD_REQUIRED" in _codes(c007, "ERROR")


def test_resolution_chain_is_contiguous(c007):
    """PROV.SA.EXECUTION: step n output = step n+1 input."""
    c007["textPassages"][0]["groundings"][0]["steps"][1]["inputValue"] = "CFTR gene"
    assert "CHAIN_CONTIGUITY" in _codes(c007, "ERROR")


def test_superseded_line_must_be_invalidated(c005):
    """EINT.FLAT_COLLAPSE / D-052: corrections are new lines; the old one is invalidated."""
    lines = c005["statement"]["hasEvidenceLines"]
    lines.append({**lines[0], "id": "sieve:el/ds-doid-dispute-v2", "supersedes": [lines[0]["id"]]})
    assert "SUPERSEDED_NOT_INVALIDATED" in _codes(c005, "ERROR")
    lines[0]["validity"] = "INVALIDATED"
    assert "SUPERSEDED_NOT_INVALIDATED" not in _codes(c005)


def test_blind_approval_adds_no_evidence(c006):
    """D-066: a no-look approval contributes no evidence line."""
    decision = c006["statement"]["assertionDecisions"][0]
    decision.update(reviewDepth="NONE", evidenceLine="sieve:el/q90-record")
    assert "BLIND_APPROVAL_EVIDENCE" in _codes(c006, "ERROR")


def test_issues_name_their_requirement(c007):
    c007["statement"]["predicate"] = {"code": "skos:exactMatch"}
    issue = next(i for i in check_packet(c007) if i.code == "PREDICATE_BINDING")
    assert issue.requirement == "C007"


def test_unrecorded_read_coverage_warns(c007):
    """D-059: legacy data may say NOT_RECORDED explicitly; it is flagged, not silently accepted."""
    act = c007["statement"]["hasEvidenceLines"][1]["contributions"][0]
    act.update(readCoverage="NOT_RECORDED", accessStatus="NOT_RECORDED")
    assert "READ_COVERAGE" not in _codes(c007, "ERROR")
    assert "READ_COVERAGE_NOT_RECORDED" in _codes(c007, "WARNING")
