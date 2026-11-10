# Python API Reference

!!! warning "Application modules not yet migrated"
    `sieve.datamodel`, `sieve.datamodel.codegen`, `sieve.profile_checks` and
    `sieve.traceability` work with the current profile. `sieve.datamodel.loaders`,
    `sieve.store`, `sieve.packet_ingest`, `sieve.packet_export` and `sieve.scoring`
    still target the pre-profile model and fail at import or at run time. They are
    being migrated (`issues/issue_migrate_app_to_profile.md`). Their signatures are
    listed below as they are in the source.

For what the model fields mean, see the [Data Model](data-model.md).

| Module | Purpose | Status |
|--------|---------|--------|
| `sieve.datamodel` | Generated Pydantic models | current |
| `sieve.datamodel.codegen` | Generate the models from the schema | current |
| `sieve.profile_checks` | Profile constraints beyond linkml-validate | current |
| `sieve.traceability` | Requirement-to-schema traceability | current |
| `sieve.datamodel.loaders` | Polymorphic packet loading | pre-profile |
| `sieve.store` | `PacketStore`, DuckDB persistence | pre-profile |
| `sieve.packet_ingest` | Validate and ingest YAML packets | pre-profile |
| `sieve.packet_export` | RDF and YAML export | pre-profile |
| `sieve.scoring` | Net Evidence Ratio | pre-profile |
| `sieve.auth` | ORCID OAuth and curator authorisation | model-independent |

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
`sieve.datamodel.sieve_models`. Field names are the schema's camelCase names. The
`type` slot is a type designator, so validating a dict picks the concrete classes:

```python
import yaml
from sieve.datamodel import EvidencePacket

data = yaml.safe_load(open("tests/data/profile/valid/c007_cf_cftr_panel.yaml"))
packet = EvidencePacket.model_validate(data)
type(packet.statement).__name__          # "DiseaseAttributeStatement"
packet.statement.score                   # 0.97
packet.text_passages[0].quote_verification # "NOT_CHECKED"
```

---

## sieve.datamodel.codegen

```python
from sieve.datamodel.codegen import generate_pydantic, fix_date_shadowing

def generate_pydantic(schema_path: str | Path) -> str   # module source for the schema
def fix_date_shadowing(code: str) -> str                # alias the date type as _Date
```

The core's `Activity.date` slot shadows the `date` type inside generated class bodies
on Python 3.10; `fix_date_shadowing` refers to the type through `_Date` instead. Run it
through `just gen-pydantic`, or directly:

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
| `DANGLING_REFERENCE` | ERROR | a line references an item not in the packet (EINT.REQUIRED) |
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

---

## sieve.datamodel.loaders (pre-profile)

```python
def load_packet(path: Path) -> EvidencePacket
def packet_from_dict(data: dict[str, Any]) -> EvidencePacket
EVIDENCE_ITEM_TYPES: dict[str, type[BaseModel]]
```

Dispatched inlined evidence items to their concrete class by `type` before validating.
It imports classes that no longer exist; `EvidencePacket.model_validate` replaces it.

## sieve.store (pre-profile)

```python
class PacketStore:
    def __init__(self, db_path: str = "data/sieve.duckdb")   # ":memory:" for tests
    def insert_packet(self, packet: EvidencePacket) -> str   # upsert; stores the NER
    def get_packet(self, packet_id: str) -> EvidencePacket | None
    def list_packets(self, status: str | None = None) -> list[dict]
    def get_stats(self) -> dict[str, int]                    # {status: count}
    def update_status(self, packet_id: str, status: str) -> None
    def set_item_rating(self, packet_id: str, item_id: str, rating: str) -> None
    def get_decisions(self, packet_id: str) -> list[dict]    # newest first
    def record_decision(self, decision: CurationDecision) -> str
    def close(self) -> None
```

## sieve.packet_ingest (pre-profile)

```python
def validate_packet_dict(data: dict[str, Any]) -> list           # [] means valid
def ingest_packet_file(path: Path, store: PacketStore) -> str
def ingest_packet_directory(path: Path, store: PacketStore) -> dict[str, Any]
    # {"files": int, "success": int, "errors": int, "error_details": [...]}
```

## sieve.packet_export (pre-profile)

```python
def packet_to_yaml(packet: EvidencePacket) -> str
def export_packets_to_yaml(packets: list[EvidencePacket], output_path: Path) -> None
def packet_to_rdf(packet: EvidencePacket, graph: Graph | None = None) -> Graph
def export_packets_to_rdf(packets, output_path=None, format="turtle") -> str
def expand_curie(curie: str | None, converter: curies.Converter) -> URIRef | None
def get_obo_converter() -> curies.Converter
```

`packet_to_rdf` emitted an `owl:Axiom` for packets with status `ACCEPTED`, `REJECTED` or
`CONTROVERSIAL` and skipped the rest with a warning.

## sieve.scoring (pre-profile)

```python
def net_evidence_ratio(packet: EvidencePacket) -> float   # (S+ - S-) / (S+ + S- + S0)
def line_score(line) -> float     # score, else strong=1.0 / moderate=0.6 / weak=0.3, else 1.0
```

To be replaced by the inclusion score S of the claim type's `AggregationRule` (see
[Data Model](data-model.md#the-inclusion-score)).

---

## sieve.auth

ORCID OAuth login and curator authorisation for the Streamlit review UI. It does not
use the data model.

```python
from sieve.auth import (
    OrcidUser,                  # dataclass: orcid, name, access_token
    AuthorizedCurator,          # dataclass: orcid, name, role ("admin"|"curator")
    is_dev_mode,                # () -> bool  (SIEVE_DEV_MODE=true bypasses auth)
    is_orcid_configured,        # () -> bool
    get_orcid_config,           # () -> dict
    get_authorization_url,      # () -> str
    exchange_code_for_token,    # (code: str) -> OrcidUser | None
    load_authorized_curators,   # () -> dict[str, AuthorizedCurator]  (keyed by ORCID)
    is_authorized_curator,      # (orcid: str | None) -> bool  (True in dev mode)
    get_curator_role,           # (orcid: str | None) -> str | None
    is_admin,                   # (orcid: str | None) -> bool  (True in dev mode)
    get_curator_info,           # () -> tuple[str | None, str | None]  (orcid, name)
)
```

Authorised curators are read from `curators.yaml` (path overridable via the
`CURATORS_FILE` env var), cached for 60 seconds:

```yaml
curators:
  - orcid: "0000-0001-2345-6789"
    name: "Dr. Jane Smith"
    role: admin
```

Streamlit-bound helpers (`get_current_user`, `set_current_user`, `logout`,
`handle_oauth_callback`, `render_login_ui`) require an active Streamlit session.
