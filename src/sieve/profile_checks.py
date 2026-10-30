"""Profile constraints that LinkML validation cannot express.

linkml-validate (JSON Schema) covers ranges, enums, cardinality and the class rules
in ``schema/sieve.yaml``. This module adds the checks that need to look inside a
Coding, follow references between packet objects, or depend on the claim type:

- predicate value sets, declared as ``bindings`` on each claim type's ``predicate``;
- the claim-evidence matrix, declared as the ``permitted_evidence`` annotation;
- read coverage on document-based lines, methods on AI and rule-based lines;
- resolution-chain contiguity, supersession, blind approvals;
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
    "externalRecords",
    "concordantAssertions",
    "textPassages",
    "publications",
    "webPages",
    "guidelines",
    "computationalScores",
)
DOCUMENT_CLASSES = {"Publication", "WebPage", "GuidelineDocument", "TextPassage"}
AUTOMATED_METHODS = {"LLM_JUDGEMENT", "RULE_BASED_STRENGTH"}
CONCORDANCE_CLASSES = {"ConcordantAssertion"}


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

    >>> sorted(permitted_evidence(_schema_view(), "MappingStatement"))
    ['ComputationalScore', 'ConcordantAssertion', 'ExternalRecord']
    """
    annotations = sv.get_class(claim_type).annotations or {}
    value = annotations["permitted_evidence"].value if "permitted_evidence" in annotations else ""
    return set(str(value).split())


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
        if statement.get("objectObsoleteInSourceVersion") and statement["subject"] in obsolete_terms:
            yield Issue("WARNING", "OBSOLETE_TO_OBSOLETE", "both sides obsolete: flag for review and deletion", "C006")

    if claim_type == "DefinitionStatement":
        has_source = statement.get("hasEvidenceLines") or statement.get("hasEvidence") or statement.get("origin")
        if not has_source:
            yield Issue("WARNING", "DEFINITION_WITHOUT_SOURCE", "definition has no evidence and no origin (backlog)", "C002")

    for decision in statement.get("assertionDecisions") or []:
        if decision.get("reviewDepth") == "NONE" and decision.get("evidenceLine"):
            yield Issue("ERROR", "BLIND_APPROVAL_EVIDENCE", f"{decision['id']}: a no-look approval adds no evidence", "PROV.ASSERTION.METHOD_TYPES")


def _check_lines(sv: SchemaView, statement: dict, items: dict[str, dict]) -> Iterator[Issue]:
    claim_type = statement["type"]
    lines = {line["id"]: line for line in statement.get("hasEvidenceLines") or []}
    permitted = permitted_evidence(sv, claim_type)
    matrix_req = "MATRIX." + _claim_requirement(sv, claim_type)
    for line in lines.values():
        referenced = []
        for ref in line.get("hasEvidenceItems") or []:
            if ref in lines:
                continue  # higher-order line (EINT.STACKING)
            if ref not in items:
                yield Issue("ERROR", "DANGLING_REFERENCE", f"{line['id']} references unknown item {ref}", "EINT.REQUIRED")
                continue
            item_type = items[ref]["type"]
            referenced.append(item_type)
            if item_type not in permitted:
                yield Issue("ERROR", "EVIDENCE_NOT_PERMITTED", f"{item_type} is not evidence for {claim_type}", matrix_req)

        if claim_type == "NegativeSubclassStatement" and line["directionOfEvidenceProvided"] == "supports":
            if CONCORDANCE_CLASSES & set(referenced):
                yield Issue("WARNING", "CONCORDANCE_DIRECTION", f"{line['id']}: a source asserting the positive subclass disputes", "MATRIX.C005")

        acts = line.get("contributions") or []
        if DOCUMENT_CLASSES & set(referenced):
            for act in acts:
                if not (act.get("readCoverage") and act.get("accessStatus")):
                    yield Issue("ERROR", "READ_COVERAGE", f"{act['id']}: document-based line without read coverage / access status", "PROV.SA.EXECUTION")
                elif "NOT_RECORDED" in (act["readCoverage"], act["accessStatus"]):
                    yield Issue("WARNING", "READ_COVERAGE_NOT_RECORDED", f"{act['id']}: read coverage / access status not recorded", "PROV.SA.EXECUTION")
        for act in acts:
            if act.get("methodType") in AUTOMATED_METHODS and not act.get("specifiedBy"):
                yield Issue("ERROR", "METHOD_REQUIRED", f"{act['id']}: AI / rule-based interpretation without its method", "PROV.INTERP.METHODS")
        if any(act.get("methodType") == "RULE_BASED_STRENGTH" for act in acts) and not line.get("computedByRule"):
            yield Issue("ERROR", "METHOD_REQUIRED", f"{line['id']}: rule-based line without computedByRule", "PROV.INTERP.METHODS")

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
            if before["outputValue"] != after["inputValue"]:
                yield Issue(
                    "ERROR",
                    "CHAIN_CONTIGUITY",
                    f"{chain['id']}: {before['id']} outputs {before['outputValue']!r} but {after['id']} reads {after['inputValue']!r}",
                    "PROV.SA.EXECUTION",
                )


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
    return issues
