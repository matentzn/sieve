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
