"""Profile constraints that LinkML validation cannot express.

linkml-validate (JSON Schema) covers ranges, enums, cardinality and the class rules
in ``schema/sieve.yaml``. This module adds the checks that need to look inside a
Coding, follow references between packet objects, or depend on the claim type:

- predicate value sets, declared as ``bindings`` on each claim type's ``predicate``;
- the claim-evidence matrix, declared as the ``permitted_evidence`` annotation;
- read coverage on document-based lines, methods on AI and rule-based lines;
- resolution-chain contiguity, supersession, blind approvals;
- competing claims (D-069): one disputing line per claim, only for exclusive claim
  types, and never an automated acceptance while it is live;
- self-containment (D-051) and unknown human agents;
- the WARNING-severity states of the Mondo decisions (D-011, D-029).

Every issue names the requirement it enforces, so a failure can be traced back to
the requirements workbook.
"""

from dataclasses import dataclass
from functools import lru_cache
from typing import Any, Iterator, Literal

from linkml_runtime.utils.schemaview import SchemaView

from sieve.traceability import SCHEMA

Severity = Literal["ERROR", "WARNING"]

ITEM_LISTS = (
    "external_records",
    "prior_claims",
    "text_passages",
    "publications",
    "web_pages",
    "guidelines",
    "computational_scores",
)
DOCUMENT_CLASSES = {"Publication", "WebPage", "GuidelineDocument", "TextPassage"}
AUTOMATED_METHODS = {"LLM_JUDGEMENT", "RULE_BASED_STRENGTH"}
# Slots that only the packet's own claim may carry, never a prior claim.
CURATION_SLOTS = ("review_state", "assertion_decisions", "origin", "proposing_channel", "has_evidence_lines", "score")


@dataclass(frozen=True)
class Issue:
    """One profile violation (ERROR) or reviewable state (WARNING)."""

    severity: Severity
    code: str
    message: str
    requirement: str


@lru_cache(maxsize=1)
def _schema_view() -> SchemaView:
    return SchemaView(str(SCHEMA))


def predicate_value_set(sv: SchemaView, claim_type: str) -> set[str]:
    """Return the predicate CURIEs bound to a claim type's ``predicate`` slot.

    >>> sorted(predicate_value_set(_schema_view(), "SynonymStatement"))[:2]
    ['oboInOwl:hasBroadSynonym', 'oboInOwl:hasExactSynonym']
    """
    slot = sv.induced_slot("predicate", claim_type)
    values: set[str] = set()
    for binding in slot.bindings or []:
        enum = sv.get_enum(binding.range)
        values |= {pv.meaning for pv in enum.permissible_values.values() if pv.meaning}
    return values


def permitted_evidence(sv: SchemaView, claim_type: str) -> set[str]:
    """Return the evidence-item classes permitted for a claim type (claim-evidence matrix).

    ``SieveStatement`` stands for any structured prior claim (any claim type).

    >>> sorted(permitted_evidence(_schema_view(), "MappingStatement"))
    ['ComputationalScore', 'ExternalRecord', 'SieveStatement']
    """
    annotations = sv.get_class(claim_type).annotations or {}
    value = annotations["permitted_evidence"].value if "permitted_evidence" in annotations else ""
    return set(str(value).split())


@lru_cache(maxsize=1)
def _claim_types() -> frozenset[str]:
    """Every claim-type Statement class (the classes a prior claim can have)."""
    return frozenset(_schema_view().class_descendants("SieveStatement"))


def _evidence_form(item_type: str) -> str:
    """The class a permitted_evidence entry names: claim types collapse to SieveStatement."""
    return "SieveStatement" if item_type in _claim_types() else item_type


def _items(packet: dict) -> dict[str, dict]:
    """Index every evidence item in the packet by id."""
    return {item["id"]: item for key in ITEM_LISTS for item in packet.get(key) or []}


def _claim_requirement(sv: SchemaView, claim_type: str) -> str:
    """The CT requirement (C00N) a claim-type class realises."""
    annotations = sv.get_class(claim_type).annotations or {}
    ids = str(annotations["requirements"].value).split() if "requirements" in annotations else []
    return next((i for i in ids if i.startswith("C0")), claim_type)


def _check_statement(sv: SchemaView, statement: dict, obsolete_terms: set[str]) -> Iterator[Issue]:
    claim_type = statement["type"]
    req = _claim_requirement(sv, claim_type)
    code = (statement.get("predicate") or {}).get("code")
    allowed = predicate_value_set(sv, claim_type)
    if allowed and code not in allowed:
        yield Issue("ERROR", "PREDICATE_BINDING", f"{code} is not a {claim_type} predicate ({sorted(allowed)})", req)

    negated = bool(statement.get("negated"))
    if claim_type == "NegativeSubclassStatement" and not negated:
        yield Issue("ERROR", "NEGATION", "a NegativeSubclassStatement must have negated = true", "C005")
    if claim_type == "SubclassStatement" and negated:
        yield Issue("ERROR", "NEGATION", "a negated subclass claim must be a NegativeSubclassStatement", "C005")

    if claim_type == "MappingStatement":
        if statement.get("preferred") and code != "skos:exactMatch":
            yield Issue("ERROR", "PREFERRED_NOT_EXACT", "preferred is only valid on skos:exactMatch", "C006")
        if statement.get("object_obsolete_in_source_version") and statement["subject"] in obsolete_terms:
            yield Issue("WARNING", "OBSOLETE_TO_OBSOLETE", "both sides obsolete: flag for review and deletion", "C006")

    if claim_type == "DefinitionStatement":
        has_source = statement.get("has_evidence_lines") or statement.get("has_evidence") or statement.get("origin")
        if not has_source:
            yield Issue("WARNING", "DEFINITION_WITHOUT_SOURCE", "definition has no evidence and no origin (backlog)", "C002")

    for decision in statement.get("assertion_decisions") or []:
        if decision.get("review_depth") == "NONE" and decision.get("evidence_line"):
            yield Issue("ERROR", "BLIND_APPROVAL_EVIDENCE", f"{decision['id']}: a no-look approval adds no evidence", "PROV.ASSERTION.METHOD_TYPES")


def _check_lines(sv: SchemaView, statement: dict, items: dict[str, dict]) -> Iterator[Issue]:
    claim_type = statement["type"]
    lines = {line["id"]: line for line in statement.get("has_evidence_lines") or []}
    permitted = permitted_evidence(sv, claim_type)
    matrix_req = "MATRIX." + _claim_requirement(sv, claim_type)
    for line in lines.values():
        referenced = []
        for ref in line.get("has_evidence_items") or []:
            if ref in lines:
                continue  # higher-order line (EINT.STACKING)
            if ref not in items:
                yield Issue("ERROR", "DANGLING_REFERENCE", f"{line['id']} references unknown item {ref}", "EINT.REQUIRED")
                continue
            item_type = items[ref]["type"]
            referenced.append(_evidence_form(item_type))
            if _evidence_form(item_type) not in permitted:
                yield Issue("ERROR", "EVIDENCE_NOT_PERMITTED", f"{item_type} is not evidence for {claim_type}", matrix_req)

        if claim_type == "NegativeSubclassStatement" and line["direction_of_evidence_provided"] == "supports":
            if "SieveStatement" in referenced:
                yield Issue("WARNING", "CONCORDANCE_DIRECTION", f"{line['id']}: a source asserting the positive subclass disputes", "MATRIX.C005")

        acts = line.get("contributions") or []
        if DOCUMENT_CLASSES & set(referenced):
            for act in acts:
                if not (act.get("read_coverage") and act.get("access_status")):
                    yield Issue("ERROR", "READ_COVERAGE", f"{act['id']}: document-based line without read coverage / access status", "PROV.SA.EXECUTION")
                elif "NOT_RECORDED" in (act["read_coverage"], act["access_status"]):
                    yield Issue("WARNING", "READ_COVERAGE_NOT_RECORDED", f"{act['id']}: read coverage / access status not recorded", "PROV.SA.EXECUTION")
        for act in acts:
            if act.get("method_type") in AUTOMATED_METHODS and not act.get("specified_by"):
                yield Issue("ERROR", "METHOD_REQUIRED", f"{act['id']}: AI / rule-based interpretation without its method", "PROV.INTERP.METHODS")
        if any(act.get("method_type") == "RULE_BASED_STRENGTH" for act in acts) and not line.get("computed_by_rule"):
            yield Issue("ERROR", "METHOD_REQUIRED", f"{line['id']}: rule-based line without computed_by_rule", "PROV.INTERP.METHODS")

        for old in line.get("supersedes") or []:
            if old in lines and lines[old].get("validity", "VALID") != "INVALIDATED":
                yield Issue("ERROR", "SUPERSEDED_NOT_INVALIDATED", f"{old} is superseded by {line['id']} but still VALID", "EINT.FLAT_COLLAPSE")


def _chains(packet: dict) -> Iterator[dict]:
    for item in _items(packet).values():
        yield from item.get("groundings") or []


def _check_chains(packet: dict) -> Iterator[Issue]:
    for chain in _chains(packet):
        steps = chain.get("steps") or []
        for before, after in zip(steps, steps[1:]):
            if before["output_value"] != after["input_value"]:
                yield Issue(
                    "ERROR",
                    "CHAIN_CONTIGUITY",
                    f"{chain['id']}: {before['id']} outputs {before['output_value']!r} but {after['id']} reads {after['input_value']!r}",
                    "PROV.SA.EXECUTION",
                )


REGISTRY_ROOTS = ("InformationResource", "SourceRelease", "SieveAgent", "SieveMethod", "BatchSignOff")
SNAPSHOT_LISTS = ("resources", "releases", "agents", "methods", "aggregation_rules", "policies", "batches")


@lru_cache(maxsize=1)
def _registry_classes() -> frozenset[str]:
    """Classes whose instances live in the registry and are referenced by id."""
    sv = _schema_view()
    return frozenset(c for root in REGISTRY_ROOTS for c in sv.class_descendants(root))


def registry_references(value: Any, cls: str, path: str = "") -> Iterator[tuple[str, str, str]]:
    """Yield (path, id, expected class) for every registry reference inside ``value``.

    Walks the instance along the schema: a string in a slot whose range is a registry
    class is a reference; a dict is an inlined object, walked as its own ``type`` (or
    the slot range when it has none).
    """
    sv = _schema_view()
    if isinstance(value, list):
        for i, v in enumerate(value):
            yield from registry_references(v, cls, f"{path}[{i}]")
        return
    if not isinstance(value, dict):
        return
    cls = value.get("type", cls)
    if cls not in sv.all_classes():
        return
    for key, child in value.items():
        if key in ("id", "type") or str(key).startswith("_"):
            continue
        rng = sv.induced_slot(key, cls).range
        if rng not in sv.all_classes():
            continue
        children = child if isinstance(child, list) else [child]
        for i, c in enumerate(children):
            where = f"{path}.{key}" + (f"[{i}]" if isinstance(child, list) else "")
            if isinstance(c, str) and rng in _registry_classes():
                yield where, c, rng
            elif isinstance(c, dict):
                yield from registry_references(c, rng, where)


def _check_self_contained(sv: SchemaView, packet: dict) -> Iterator[Issue]:
    """Every registry reference in the packet resolves to its own reference snapshot."""
    snapshot = packet.get("reference_snapshot") or {}
    index = {entry["id"]: entry.get("type") for key in SNAPSHOT_LISTS for entry in snapshot.get(key) or []}
    for where, ref, expected in registry_references(packet, "EvidencePacket"):
        found = index.get(ref)
        if found is None:
            yield Issue("ERROR", "UNRESOLVED_REFERENCE", f"{where}: {ref} is not in the packet's reference_snapshot", "PROV.ASSERTION.METHODS")
        elif found not in sv.class_descendants(expected):
            yield Issue("ERROR", "UNRESOLVED_REFERENCE", f"{where}: {ref} is a {found}, expected a {expected}", "PROV.ASSERTION.METHODS")


AUTOMATED_ROUTES = {"DELEGATED_POLICY", "PROVIDER_AUTHORITY"}


def _check_competing_claims(packet: dict, items: dict[str, dict]) -> Iterator[Issue]:
    """D-069: one disputing competing-claim line, only for exclusive claim types."""
    statement = packet["statement"]
    lines = statement.get("has_evidence_lines") or []
    competing = [
        line for line in lines
        if any(a.get("method_type") == "COMPETING_CLAIM" for a in line.get("contributions") or [])
    ]
    live = [line for line in competing if line.get("validity", "VALID") != "INVALIDATED"]
    if len(live) > 1:
        yield Issue("ERROR", "COMPETING_CLAIM_LINE", "more than one live competing-claim line; combine all competitors in one", "EINT.CONTRADICTION")
    for line in competing:
        if line["direction_of_evidence_provided"] != "disputes":
            yield Issue("ERROR", "COMPETING_CLAIM_LINE", f"{line['id']}: a competing-claim line disputes", "EINT.CONTRADICTION")
        for ref in line.get("has_evidence_items") or []:
            item = items.get(ref, {})
            if item.get("type") not in _claim_types() or item.get("own_log_odds") is None or not item.get("log_odds_basis"):
                yield Issue("ERROR", "COMPETING_CLAIM_LINE", f"{line['id']}: {ref} must be a prior claim with own_log_odds and log_odds_basis", "EINT.CONTRADICTION")
    if competing:
        rules = [
            r for r in (packet.get("reference_snapshot") or {}).get("aggregation_rules") or []
            if r.get("claim_type") == statement["type"]
        ]
        if not any(r.get("exclusive") for r in rules):
            yield Issue("ERROR", "COMPETING_CLAIM_LINE", f"{statement['type']} is not exclusive under its aggregation rule", "EINT.CONTRADICTION")
    if live:
        for decision in statement.get("assertion_decisions") or []:
            if decision.get("route") in AUTOMATED_ROUTES and decision.get("outcome") == "ACCEPTED":
                yield Issue("ERROR", "CONTESTED_AUTO_ACCEPT", f"{decision['id']}: no automated acceptance while a competing claim is live", "EINT.CONTRADICTION")


def _check_agents(packet: dict) -> Iterator[Issue]:
    """Unknown human interpreters are persons; a sign-off by one is flagged (D-049)."""
    agents = {a["id"]: a for a in (packet.get("reference_snapshot") or {}).get("agents") or []}
    unknown = {i for i, a in agents.items() if a.get("identity_known") is False}
    for agent_id in unknown:
        if agents[agent_id].get("subtype") != "person":
            yield Issue("ERROR", "UNKNOWN_AGENT", f"{agent_id}: an agent of unknown identity must be a person", "PROV.INTERP.AGENT")
    for decision in packet["statement"].get("assertion_decisions") or []:
        signers = {decision.get("contributor"), *(decision.get("participants") or [])}
        if signers & unknown:
            yield Issue("WARNING", "UNKNOWN_HUMAN_DECISION", f"{decision['id']}: signed off by a person of unknown identity", "PROV.ASSERTION.AGENT")


def _check_prior_claims(sv: SchemaView, packet: dict) -> Iterator[Issue]:
    """Prior claims are claims, not curation records; the packet's own claim is curated."""
    if not packet["statement"].get("review_state"):
        yield Issue("ERROR", "REVIEW_STATE", "the packet's own claim needs a review_state", "C006")
    for claim in packet.get("prior_claims") or []:
        carried = [s for s in CURATION_SLOTS if claim.get(s) not in (None, [], "")]
        if carried:
            yield Issue("ERROR", "PRIOR_CLAIM_CURATION", f"{claim['id']}: curation slots {carried} belong to the packet's own claim", "EI.PRIOR_CLAIM.DIRECT_STRUCTURED")
        if (claim.get("own_log_odds") is None) != (not claim.get("log_odds_basis")):
            yield Issue("ERROR", "COMPETING_CLAIM_LINE", f"{claim['id']}: own_log_odds and log_odds_basis go together", "EINT.CONTRADICTION")
        code = (claim.get("predicate") or {}).get("code")
        allowed = predicate_value_set(sv, claim["type"])
        if allowed and code not in allowed:
            yield Issue("ERROR", "PREDICATE_BINDING", f"{claim['id']}: {code} is not a {claim['type']} predicate", _claim_requirement(sv, claim["type"]))


def check_packet(packet: dict[str, Any], obsolete_terms: set[str] | frozenset[str] = frozenset()) -> list[Issue]:
    """Return the profile issues of one EvidencePacket (as loaded from YAML / JSON).

    ``obsolete_terms`` lists Mondo terms known to be obsolete. Subject obsolescence
    is read from term status, not stored on mappings (D-009).
    """
    sv = _schema_view()
    statement = packet["statement"]
    issues = list(_check_statement(sv, statement, set(obsolete_terms)))
    issues += _check_lines(sv, statement, _items(packet))
    issues += _check_chains(packet)
    issues += _check_self_contained(sv, packet)
    issues += _check_competing_claims(packet, _items(packet))
    issues += _check_agents(packet)
    issues += _check_prior_claims(sv, packet)
    return issues
