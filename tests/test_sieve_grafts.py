"""Grafted sieve-specific slots resolve on the evidence-item classes."""

from pathlib import Path

from linkml_runtime import SchemaView

SIEVE = Path(__file__).parent.parent / "schema" / "sieve.yaml"
CURATED_ITEMS = [
    "ConcordanceItem",
    "AgentContribution",
    "SieveDocument",
    "SieveDataItem",
    "SieveStudyResult",
    "ComputationalResult",
]


def test_curated_evidence_slots_present_on_all_items():
    sv = SchemaView(str(SIEVE))
    for cls in CURATED_ITEMS:
        names = {s.name for s in sv.class_induced_slots(cls)}
        assert {"rating", "eco_code", "eco_label"} <= names, f"{cls} missing graft"


def test_curation_decision_and_provenance_grafts():
    sv = SchemaView(str(SIEVE))
    assert sv.get_class("CurationDecision") is not None
    assert sv.get_enum("DecisionType") is not None
    activity_slots = {s.name for s in sv.class_induced_slots("CurationActivity")}
    assert {"pull_request", "issue", "created_with"} <= activity_slots
    concordance_slots = {s.name for s in sv.class_induced_slots("ConcordanceItem")}
    assert "mapping_set" in concordance_slots
