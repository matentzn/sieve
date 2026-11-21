# Python API Reference

For what the model fields mean, see the [Data Model](data-model.md).

| Module | Purpose |
|--------|---------|
| `sieve.datamodel` | Generated Pydantic models |
| `sieve.datamodel.codegen` | Generate the models from the schema |
| `sieve.packet_items` | Walk the nested evidence items of a packet |
| `sieve.profile_checks` | Profile constraints beyond linkml-validate |
| `sieve.inclusion_score` | Reference inclusion score S of a packet |
| `sieve.traceability` | Requirement-to-schema traceability |

The application layer of the pre-profile model (Streamlit review app, DuckDB store,
ingest / export, scoring, CLI) was removed on 2026-11-20; it is to be rebuilt on the
profile.

---

## sieve.datamodel

Pydantic v2 classes generated from `schema/sieve.yaml` into
`sieve.datamodel.sieve_models`. The package re-exports the main ones:

```python
from sieve.datamodel import (
    EvidencePacket, SieveRegistry,
    SieveStatement,                       # abstract; the ten claim types below
    TermExistenceStatement, DefinitionStatement, SynonymStatement,
    SubclassStatement, NegativeSubclassStatement, MappingStatement,
    DiseaseAttributeStatement, SubsetMembershipStatement,
    MetaclassStatement, ValueSetMembershipStatement,
    ExternalRecord, TextPassage, Publication, WebPage,
    ComputationalScore, InformationResource,
    SieveEvidenceLine, InterpretationActivity, AssertionDecision,
    SieveAgent, DecisionPolicy,
)
```

Everything else (`GuidelineDocument`, `OriginEvent`, `ResolutionChain`,
`AlignmentStep`, `AggregationRule`, `BatchSignOff`, the enums, ...) is in
`sieve.datamodel.sieve_models`. Field names are the schema's snake_case names. The
`type` slot is a type designator, so validating a dict picks the concrete classes,
nested evidence items included:

```python
import yaml
from sieve.datamodel import EvidencePacket

data = yaml.safe_load(open("tests/data/profile/valid/c007_cf_cftr_panel.yaml"))
packet = EvidencePacket.model_validate(data)
type(packet.statement).__name__          # "DiseaseAttributeStatement"
packet.statement.score                   # 0.97
passage = packet.statement.has_evidence_lines[1].has_evidence_items[0]
type(passage).__name__                   # "TextPassage"
passage.quote_verification               # "NOT_CHECKED"
```

`sieve.packet_items` walks the nested items without the Pydantic model:
`iter_items(packet)` yields every item copy, `item_copies(packet)` groups them by id,
and `find_item(packet, id)` returns one.

---

## sieve.datamodel.codegen

```python
from sieve.datamodel.codegen import generate_pydantic, fix_date_shadowing, raise_recursion_limit

def generate_pydantic(schema_path: str | Path) -> str   # module source for the schema
def fix_date_shadowing(code: str) -> str                # alias the date type as _Date
def raise_recursion_limit(code: str) -> str             # lift the recursion limit in the module
```

The core's `Activity.date` slot shadows the `date` type inside generated class bodies
on Python 3.10; `fix_date_shadowing` refers to the type through `_Date` instead. The
core's `type` slot is a type designator, so every slot ranged on a core class becomes a
union of its subclasses; `raise_recursion_limit` lifts the recursion limit in the
generated module, because Pydantic needs more than 1000 frames to build those models.
Run it through `just gen-pydantic`, or directly:

```bash
uv run python -m sieve.datamodel.codegen schema/sieve.yaml src/sieve/datamodel/sieve_models.py
```

---

## sieve.profile_checks

```python
from sieve.profile_checks import check_packet, Issue, predicate_value_set, permitted_evidence

def check_packet(packet: dict[str, Any],
                 obsolete_terms: set[str] | frozenset[str] = frozenset()) -> list[Issue]

@dataclass(frozen=True)
class Issue:
    severity: Literal["ERROR", "WARNING"]
    code: str            # e.g. "PREDICATE_BINDING", "EVIDENCE_NOT_PERMITTED"
    message: str
    requirement: str     # the requirement ID the check enforces

def predicate_value_set(sv: SchemaView, claim_type: str) -> set[str]
def permitted_evidence(sv: SchemaView, claim_type: str) -> set[str]
```

`check_packet` takes a packet as a plain dict (as loaded from YAML or JSON) and returns
an empty list when it passes. `obsolete_terms` lists Mondo terms known to be obsolete;
subject obsolescence is read from term status, not stored on mappings.

| Code | Severity | Requirement |
|---|---|---|
| `PREDICATE_BINDING` | ERROR | predicate not in the claim type's value set (C00N) |
| `NEGATION` | ERROR | `NegativeSubclassStatement` without `negated: true`, or a negated `SubclassStatement` (C005) |
| `PREFERRED_NOT_EXACT` | ERROR | `preferred` on a mapping that is not `skos:exactMatch` (C006) |
| `NOT_AN_EVIDENCE_ITEM` | ERROR | a nested evidence slot holds something that is not an evidence item (EINT.REQUIRED) |
| `COPY_DIVERGENCE` | ERROR | two copies of a nested item share an id but differ (EINT.REQUIRED) |
| `DANGLING_REFERENCE` | ERROR | a link that stays an id (`supersedes`, `replacement_line`, `derived_from`, `evidence_line`) names no item or line in the packet (EINT.REQUIRED) |
| `EVIDENCE_NOT_PERMITTED` | ERROR | item class not in the claim-evidence matrix (MATRIX.C00N) |
| `READ_COVERAGE` | ERROR | document-based line without `read_coverage` / `access_status` (PROV.SA.EXECUTION) |
| `METHOD_REQUIRED` | ERROR | AI or rule-based line without `specified_by`, or rule-based line without `computed_by_rule` (PROV.INTERP.METHODS) |
| `SUPERSEDED_NOT_INVALIDATED` | ERROR | a superseded line is still VALID (EINT.FLAT_COLLAPSE) |
| `CHAIN_CONTIGUITY` | ERROR | a resolution step does not read the previous step's output (PROV.SA.EXECUTION) |
| `BLIND_APPROVAL_EVIDENCE` | ERROR | a `review_depth: NONE` decision contributes an evidence line |
| `OBSOLETE_TO_OBSOLETE`, `DEFINITION_WITHOUT_SOURCE`, `CONCORDANCE_DIRECTION`, `READ_COVERAGE_NOT_RECORDED` | WARNING | states that need a person |

```python
import yaml
from sieve.profile_checks import check_packet

packet = yaml.safe_load(open("tests/data/profile/valid/c005_down_syndrome_not_hereditary.yaml"))
check_packet(packet)                     # []
packet["statement"]["predicate"]["code"] = "skos:exactMatch"
check_packet(packet)
# [Issue(severity='ERROR', code='PREDICATE_BINDING',
#        message="skos:exactMatch is not a NegativeSubclassStatement predicate (['owl:equivalentClass', 'rdfs:subClassOf'])",
#        requirement='C005')]
```

---

## sieve.traceability

```python
from sieve.traceability import (
    SCHEMA, CORE_SCHEMA, REQUIREMENTS_TSV, TRACEABILITY_YAML,   # paths
    load_requirements,     # () -> dict[str, dict[str, str]]  rows keyed by requirement ID
    load_traceability,     # () -> dict  {"modules": ..., "requirements": ...}
    schema_elements,       # (sv) -> list[(path, element)]  Class, Class.slot, Enum, Enum.value
    collect_annotations,   # (sv, key="requirements") -> dict[str, list[str]]
    render_markdown,       # (sv=None) -> str  the docs/requirements-traceability.md page
)
```

```python
from linkml_runtime.utils.schemaview import SchemaView
from sieve.traceability import SCHEMA, collect_annotations, load_traceability

sv = SchemaView(str(SCHEMA))
collect_annotations(sv)["C005"]
# ['SieveStatement.negated', 'NegativeSubclassStatement', 'NegativeSubclassStatement.negated',
#  'ClaimType.NegativeSubclassStatement', 'SubclassPredicate']
load_traceability()["requirements"]["C005"]["disposition"]   # 'modelled'
collect_annotations(sv, key="decisions")["D-063"]            # elements behind decision D-063
```

`just gen-traceability` writes `render_markdown()` to
`docs/requirements-traceability.md`.
