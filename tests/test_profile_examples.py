"""Example packets validate against the profile; profile constraints reject bad data."""

import copy
from pathlib import Path

import pytest
from linkml.validator import Validator
from linkml.validator.plugins import JsonschemaValidationPlugin
from linkml_runtime.utils.schemaview import SchemaView

from sieve.traceability import SCHEMA
from tests.profile_support import load_yaml

DATA = Path(__file__).parent / "data" / "profile"
VALID = sorted((DATA / "valid").glob("*.yaml"))


@pytest.fixture(scope="module")
def validator() -> Validator:
    sv = SchemaView(str(SCHEMA))
    sv.merge_imports()
    return Validator(sv.schema, validation_plugins=[JsonschemaValidationPlugin(closed=True)])


def _load(path: Path) -> dict:
    return load_yaml(path)


def _errors(validator: Validator, instance: dict, target: str = "EvidencePacket") -> list[str]:
    return [r.message for r in validator.validate(instance, target).results]


def _statement_errors(validator: Validator, packet: dict) -> list[str]:
    """Validate the packet's statement against its concrete claim-type class.

    Inside a packet the statement is polymorphic (anyOf over claim types), which hides
    the specific reason; validating it directly surfaces it.
    """
    statement = packet["statement"]
    return _errors(validator, statement, statement["type"])


@pytest.mark.parametrize("path", VALID, ids=lambda p: p.stem)
def test_valid_packets(validator, path):
    assert _errors(validator, _load(path)) == []


def test_registry_validates(validator):
    assert _errors(validator, _load(DATA / "registry.yaml"), "SieveRegistry") == []


def test_examples_cover_four_claim_types():
    types = {_load(p)["statement"]["type"] for p in VALID}
    assert {"NegativeSubclassStatement", "SynonymStatement", "DiseaseAttributeStatement", "MappingStatement"} <= types


@pytest.fixture
def c005() -> dict:
    return _load(DATA / "valid" / "c005_down_syndrome_not_hereditary.yaml")


@pytest.fixture
def c003() -> dict:
    return _load(DATA / "valid" / "c003_spoan_synonym_policy.yaml")


def test_neutral_direction_rejected(validator, c005):
    """EINT.DIRECTION: lines either support or dispute."""
    c005["statement"]["hasEvidenceLines"][0]["directionOfEvidenceProvided"] = "neutral"
    assert any("neutral" in e for e in _errors(validator, c005))


def test_line_score_outside_shared_scale_rejected(validator, c005):
    """EINT.NUMERICAL_STRENGTH: line strength lives on a shared 0-1 scale."""
    c005["statement"]["hasEvidenceLines"][0]["scoreOfEvidenceProvided"] = 1.5
    assert any("1.5" in e for e in _statement_errors(validator, c005))


def test_inclusion_score_bounded(validator, c005):
    """PROV.ASSERTION.CONFIDENCE_SCORE: S is in [-1, 1]."""
    c005["statement"]["score"] = -1.2
    assert any("-1.2" in e for e in _statement_errors(validator, c005))


def test_statement_requires_subject(validator, c005):
    """RCS.STRUCTURED_STATEMENT: SPO is on the Statement."""
    del c005["statement"]["subject"]
    assert any("subject" in e for e in _statement_errors(validator, c005))


def test_unknown_claim_type_rejected(validator, c005):
    c005["statement"]["type"] = "GeneDiseaseAssociation"
    assert _errors(validator, c005)


def test_line_requires_interpretation_act(validator, c005):
    """EINT.REQUIRED / PROV.INTERP.AGENT: every line records who interpreted it."""
    del c005["statement"]["hasEvidenceLines"][0]["contributions"]
    assert any("contributions" in e for e in _errors(validator, c005))


def test_line_confidence_needs_basis(validator, c005):
    """PROV.SA.CONFIDENCE_SCORE: a confidence states its basis."""
    del c005["statement"]["hasEvidenceLines"][0]["confidenceBasis"]
    assert any("confidenceBasis" in e for e in _statement_errors(validator, c005))


def test_step_confidence_needs_basis(validator, c005):
    step = c005["concordantAssertions"][0]["groundings"][0]["steps"][0]
    del step["confidenceBasis"]
    assert any("confidenceBasis" in e for e in _errors(validator, c005))


def test_policy_never_auto_rejects(validator, c003):
    """PROV.ASSERTION.METHOD_TYPES / D-064: automated routes can only accept."""
    c003["statement"]["assertionDecisions"][0]["outcome"] = "REJECTED"
    assert any("ACCEPTED" in e for e in _statement_errors(validator, c003))


def test_policy_decision_names_its_policy(validator, c003):
    del c003["statement"]["assertionDecisions"][0]["policy"]
    assert any("policy" in e for e in _statement_errors(validator, c003))


def test_batch_decision_needs_review_depth(validator):
    packet = _load(DATA / "valid" / "c006_down_syndrome_icd10cm_batch.yaml")
    del packet["statement"]["assertionDecisions"][0]["reviewDepth"]
    assert any("reviewDepth" in e for e in _statement_errors(validator, packet))


def test_human_rejection_allowed(validator, c005):
    """EINT.CONTRADICTION / D-053: a human may reject; the packet is kept."""
    decision = copy.deepcopy(c005["statement"]["assertionDecisions"][-1])
    decision.update(id="sieve:dec/ds-excl-reject", outcome="REJECTED")
    c005["statement"]["assertionDecisions"].append(decision)
    assert _errors(validator, c005) == []


def test_text_passage_requires_creation_provenance(validator):
    """PROV.EI.EXECUTION / D-057: created records carry who / when / how."""
    packet = _load(DATA / "valid" / "c007_cf_cftr_panel.yaml")
    del packet["textPassages"][0]["contributions"]
    assert any("contributions" in e for e in _errors(validator, packet))


def test_external_record_requires_retrieval_metadata(validator, c005):
    """PROV.EI.RETRIEVAL_SOURCE / D-055: when and from which release a record was read."""
    del c005["externalRecords"][0]["recordMetadata"]
    assert any("recordMetadata" in e for e in _errors(validator, c005))


def test_text_passage_derives_from_its_document_by_id(validator):
    """EINT.GROUPING / D-057: a passage states its dependence on the source document."""
    packet = _load(DATA / "valid" / "c007_cf_cftr_panel.yaml")
    packet["textPassages"][0]["derivedFrom"] = ["PMID:20301428"]
    assert _errors(validator, packet) == []


def test_packet_requires_reference_snapshot(validator, c005):
    """D-051: a packet carries a frozen snapshot of the reference data it uses."""
    del c005["referenceSnapshot"]
    assert any("referenceSnapshot" in e for e in _errors(validator, c005))
