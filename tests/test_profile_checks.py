"""Profile constraints that LinkML validation cannot express (sieve.profile_checks)."""

import copy
from pathlib import Path

import pytest

from sieve.packet_items import find_item, item_copies
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
def c003() -> dict:
    return _load(DATA / "c003_spoan_synonym_policy.yaml")


@pytest.fixture
def c006() -> dict:
    return _load(DATA / "c006_down_syndrome_icd10cm_batch.yaml")


def test_predicate_must_come_from_claim_type_value_set(c007):
    """C007 / RCS.STRUCTURED_STATEMENT: predicates are bound per claim type."""
    c007["statement"]["predicate"] = {"code": "skos:exactMatch"}
    assert "PREDICATE_BINDING" in _codes(c007, "ERROR")


def test_evidence_type_must_be_permitted_for_claim_type(c005):
    """MATRIX.C005: text passages are not evidence for a negative subclass claim."""
    passage = {"id": "sieve:tp/x", "type": "TextPassage", "statement_text": "x",
               "reported_in": [{"id": "PMID:1", "type": "Publication"}]}
    c005["statement"]["has_evidence_lines"][0]["has_evidence_items"] = [passage]
    assert "EVIDENCE_NOT_PERMITTED" in _codes(c005, "ERROR")


def test_items_are_nested_in_full(c005):
    """Evidence is nested: a line carries its items, not their ids."""
    item = c005["statement"]["has_evidence_lines"][0]["has_evidence_items"][0]
    assert isinstance(item, dict) and item["type"] == "SubclassStatement"
    assert isinstance(item["reported_in"][0], dict)


def test_nested_item_must_be_an_evidence_item(c005):
    """Only evidence-item classes (records, claims, passages, documents, scores, lines) nest as evidence."""
    resource = {"id": "infores:omim", "type": "InformationResource", "default_role": "PRIMARY"}
    c005["statement"]["has_evidence_lines"][0]["has_evidence_items"].append(resource)
    assert "NOT_AN_EVIDENCE_ITEM" in _codes(c005, "ERROR")


def test_copies_with_one_id_must_be_identical(c003):
    """Copies of an item share its id and must not drift apart (D-052)."""
    copies = item_copies(c003)["OMIM:609541"]
    assert len(copies) > 1
    copies[-1]["label"] = "a drifted label"
    issues = [i for i in check_packet(c003) if i.code == "COPY_DIVERGENCE"]
    assert issues and issues[0].severity == "ERROR"
    assert "OMIM:609541" in issues[0].message


def test_id_links_must_resolve(c005):
    """Links that stay ids (supersedes, replacement_line, derived_from, evidence_line) resolve inside the packet."""
    c005["statement"]["has_evidence_lines"][0]["supersedes"] = ["sieve:el/not-in-packet"]
    assert "DANGLING_REFERENCE" in _codes(c005, "ERROR")


def test_derived_from_resolves_to_a_nested_document(c007):
    passage = find_item(c007, "sieve:tp/pmid-20301428-1")
    passage["derived_from"] = ["PMID:404"]
    assert "DANGLING_REFERENCE" in _codes(c007, "ERROR")


def test_higher_order_line_nests_the_lines_it_reads(c005):
    """EINT.STACKING: a line can interpret other lines, carried as full copies."""
    lines = c005["statement"]["has_evidence_lines"]
    stack = {**copy.deepcopy(lines[1]), "id": "sieve:el/stack",
             "has_evidence_items": [copy.deepcopy(lines[0]), copy.deepcopy(lines[1])]}
    lines.append(stack)
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
    c005["statement"]["has_evidence_lines"][0]["direction_of_evidence_provided"] = "supports"
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
    c006["statement"]["object_obsolete_in_source_version"] = "2026"
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
            "review_state": "NOT_VERIFIED",
        },
    }
    assert "DEFINITION_WITHOUT_SOURCE" in _codes(packet, "WARNING")
    assert _codes(packet, "ERROR") == set()


def test_document_based_line_needs_read_coverage(c007):
    """D-059: what was read, and whether it was paywalled, is mandatory."""
    del c007["statement"]["has_evidence_lines"][1]["contributions"][0]["access_status"]
    assert "READ_COVERAGE" in _codes(c007, "ERROR")


def test_ai_line_needs_its_workflow(c007):
    """PROV.INTERP.METHODS / D-050: AI lines name their workflow / prompt version."""
    del c007["statement"]["has_evidence_lines"][1]["contributions"][0]["specified_by"]
    assert "METHOD_REQUIRED" in _codes(c007, "ERROR")


def test_rule_based_line_needs_its_rule(c007):
    del c007["statement"]["has_evidence_lines"][0]["computed_by_rule"]
    assert "METHOD_REQUIRED" in _codes(c007, "ERROR")


def test_resolution_chain_is_contiguous(c007):
    """PROV.SA.EXECUTION: step n output = step n+1 input."""
    find_item(c007, "sieve:tp/pmid-20301428-1")["groundings"][0]["steps"][1]["input_value"] = "CFTR gene"
    assert "CHAIN_CONTIGUITY" in _codes(c007, "ERROR")


def test_prior_claim_chain_is_contiguous(c005):
    """PROV.SA.EXECUTION: the prior claim's resolution chains are checked too."""
    chain = find_item(c005, "sieve:ca/doid-14250-isa-630")["resolution_chains"][0]
    chain["steps"].append({**chain["steps"][0], "id": "sieve:step/x", "input_value": "MONDO:0000001"})
    assert "CHAIN_CONTIGUITY" in _codes(c005, "ERROR")


def test_grounding_reads_a_string(c005):
    """PROV.SA.METHOD_TYPES: grounding resolves a string; an id-to-id step is normalization."""
    step = find_item(c005, "sieve:ca/doid-14250-isa-630")["resolution_chains"][0]["steps"][0]
    assert step["category"] == "NORMALIZATION"
    assert "GROUNDING_INPUT_IS_ID" not in _codes(c005)
    step["category"] = "GROUNDING"
    assert "GROUNDING_INPUT_IS_ID" in _codes(c005, "ERROR")


def test_grounding_of_a_mention_passes(c007):
    """A string-to-id grounding (the gene symbol "CFTR" to HGNC:1884) is fine."""
    steps = find_item(c007, "sieve:tp/pmid-20301428-1")["groundings"][0]["steps"]
    assert [s["category"] for s in steps] == ["EXTRACTION", "GROUNDING"]
    assert "GROUNDING_INPUT_IS_ID" not in _codes(c007)


def test_superseded_line_must_be_invalidated(c005):
    """EINT.FLAT_COLLAPSE / D-052: corrections are new lines; the old one is invalidated."""
    lines = c005["statement"]["has_evidence_lines"]
    lines.append({**lines[0], "id": "sieve:el/ds-doid-dispute-v2", "supersedes": [lines[0]["id"]]})
    assert "SUPERSEDED_NOT_INVALIDATED" in _codes(c005, "ERROR")
    lines[0]["validity"] = "INVALIDATED"
    assert "SUPERSEDED_NOT_INVALIDATED" not in _codes(c005)


def test_blind_approval_adds_no_evidence(c006):
    """D-066: a no-look approval contributes no evidence line."""
    decision = c006["statement"]["assertion_decisions"][0]
    decision.update(review_depth="NONE", evidence_line="sieve:el/q90-record")
    assert "BLIND_APPROVAL_EVIDENCE" in _codes(c006, "ERROR")


def test_issues_name_their_requirement(c007):
    c007["statement"]["predicate"] = {"code": "skos:exactMatch"}
    issue = next(i for i in check_packet(c007) if i.code == "PREDICATE_BINDING")
    assert issue.requirement == "C007"


def test_unrecorded_read_coverage_warns(c007):
    """D-059: legacy data may say NOT_RECORDED explicitly; it is flagged, not silently accepted."""
    act = c007["statement"]["has_evidence_lines"][1]["contributions"][0]
    act.update(read_coverage="NOT_RECORDED", access_status="NOT_RECORDED")
    assert "READ_COVERAGE" not in _codes(c007, "ERROR")
    assert "READ_COVERAGE_NOT_RECORDED" in _codes(c007, "WARNING")


def test_registry_reference_must_resolve_inside_the_packet(c007):
    """D-051: a packet is self-contained; every registry reference resolves to its own snapshot."""
    c007["statement"]["assertion_decisions"][0]["aggregation_rule"] = "sieve:rule/not-in-snapshot"
    issues = [i for i in check_packet(c007) if i.code == "UNRESOLVED_REFERENCE"]
    assert issues and issues[0].severity == "ERROR"
    assert "sieve:rule/not-in-snapshot" in issues[0].message


def test_registry_reference_must_have_the_right_kind(c007):
    """A contributor must resolve to an agent, not to some other snapshot entry."""
    c007["statement"]["has_evidence_lines"][0]["contributions"][0]["contributor"] = "sieve:rule/gene-disease-v1.3"
    assert "UNRESOLVED_REFERENCE" in _codes(c007, "ERROR")


def test_snapshot_internal_references_resolve(c003):
    """References between snapshot entries (a policy's approver) must resolve too."""
    c003["reference_snapshot"]["policies"][0]["approved_by"] = "orcid:0000-0000-0000-0000"
    assert "UNRESOLVED_REFERENCE" in _codes(c003, "ERROR")


@pytest.fixture
def mds() -> dict:
    return _load(DATA / "c003_mds_competing_claim.yaml")


def test_competing_claim_example_passes(mds):
    assert _codes(mds, "ERROR") == set()


def test_contested_claim_is_never_auto_accepted(mds):
    """D-069 / D-064: no automatic acceptance while a competing-claim line is live."""
    mds["statement"]["assertion_decisions"] = [
        {"id": "sieve:dec/mds-auto", "type": "AssertionDecision", "contributor": "sieve:agent/policy-runner",
         "date": "2026-11-03", "outcome": "ACCEPTED", "route": "DELEGATED_POLICY", "policy": "sieve:policy/synonym-v2"}
    ]
    assert "CONTESTED_AUTO_ACCEPT" in _codes(mds, "ERROR")


def test_only_one_competing_claim_line(mds):
    lines = mds["statement"]["has_evidence_lines"]
    comp = next(line for line in lines if line["id"] == "sieve:el/mds-competing")
    lines.append({**comp, "id": "sieve:el/mds-competing-2"})
    assert "COMPETING_CLAIM_LINE" in _codes(mds, "ERROR")


def test_competing_claim_line_disputes(mds):
    comp = next(line for line in mds["statement"]["has_evidence_lines"] if line["id"] == "sieve:el/mds-competing")
    comp["direction_of_evidence_provided"] = "supports"
    assert "COMPETING_CLAIM_LINE" in _codes(mds, "ERROR")


def test_competing_claims_need_an_exclusive_claim_type(mds):
    """D-069: exclusivity is declared per claim type in its aggregation rule."""
    mds["reference_snapshot"]["aggregation_rules"][0]["exclusive"] = False
    assert "COMPETING_CLAIM_LINE" in _codes(mds, "ERROR")


def test_unknown_agent_must_be_a_person(c005):
    """An unknown human interpreter is a person whose identity is not recorded."""
    agent = c005["reference_snapshot"]["agents"][0]
    agent.update(identity_known=False, subtype="software")
    assert "UNKNOWN_AGENT" in _codes(c005, "ERROR")


def test_sign_off_by_unknown_human_warns(c005):
    """D-049: a decision's weight depends on who signs; an unknown signer is flagged."""
    curator = next(a for a in c005["reference_snapshot"]["agents"] if a["id"] == "orcid:0000-0001-5208-3432")
    curator["identity_known"] = False
    assert "UNKNOWN_HUMAN_DECISION" in _codes(c005, "WARNING")


DOID_CLAIM = "sieve:ca/doid-14250-isa-630"


def test_prior_claim_is_typed_by_what_it_claims(c005):
    """A source's subclass assertion is a SubclassStatement, nested in the line that cites it."""
    assert find_item(c005, DOID_CLAIM)["type"] == "SubclassStatement"
    assert _codes(c005, "ERROR") == set()


def test_prior_claim_cannot_carry_curation(c005):
    """Review state, decisions, lines and score belong to the packet's own claim."""
    find_item(c005, DOID_CLAIM)["review_state"] = "VERIFIED"
    assert "PRIOR_CLAIM_CURATION" in _codes(c005, "ERROR")


def test_packet_claim_needs_review_state(c005):
    del c005["statement"]["review_state"]
    assert "REVIEW_STATE" in _codes(c005, "ERROR")


def test_prior_claim_predicate_binding(c005):
    """Predicate value sets apply to prior claims as to the packet's own claim."""
    find_item(c005, DOID_CLAIM)["predicate"] = {"code": "skos:exactMatch"}
    assert "PREDICATE_BINDING" in _codes(c005, "ERROR")


def test_competitor_needs_its_own_log_odds(mds):
    """D-069: a claim cited by the competing-claim line carries its own log-odds."""
    del find_item(mds, "sieve:cc/mds-mtdna-depletion")["own_log_odds"]
    assert "COMPETING_CLAIM_LINE" in _codes(mds, "ERROR")
