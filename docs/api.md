# Python API Reference

SIEVE is usable as a library, not just a CLI. This page documents the public
Python API: the Pydantic data model, the loaders, the DuckDB store, and the
ingest / export / scoring / auth helpers.

Every signature below is taken from the source. For what the model *fields*
mean (statements, evidence lines, evidence items, ratings), see the
[Data Model](data-model.md) page.

| Module | Purpose |
|--------|---------|
| `sieve.datamodel` | Generated Pydantic models (`EvidencePacket`, …) |
| `sieve.datamodel.loaders` | Build packets from YAML / dicts with correct item polymorphism |
| `sieve.store` | `PacketStore` — DuckDB persistence for packets and decisions |
| `sieve.packet_ingest` | Validate and ingest YAML packets into a store |
| `sieve.packet_export` | Export packets to RDF (OWL axiom annotations) and YAML |
| `sieve.scoring` | Net Evidence Ratio over a packet's evidence lines |
| `sieve.auth` | ORCID OAuth and curator authorization (Streamlit) |

---

## sieve.datamodel

The data model is generated from `schema/sieve.yaml` into
`sieve.datamodel.sieve_models` and re-exported from `sieve.datamodel`. All
classes are Pydantic v2 `BaseModel` subclasses.

```python
from sieve.datamodel import (
    EvidencePacket,        # top-level packet: statement + evidence lines + status
    SieveStatement,        # subject / predicate / object being curated
    SieveEvidenceLine,     # one argument (direction + strength), holds items
    SieveEvidenceItem,     # base class for evidence items
    ConcordanceItem,       # evidence: another ontology/vocabulary agrees
    SieveDocument,         # evidence: a publication
    SieveDataItem,         # evidence: a database record
    SieveStudyResult,      # evidence: a study result
    ComputationalResult,   # evidence: a computation / model output
    AgentContribution,     # evidence: a person weighed in
    CurationActivity,      # who curated the packet
    CurationDecision,      # a recorded accept/reject/controversial decision
    DecisionType,          # ACCEPT | REJECT | CONTROVERSIAL
    EvidenceSynthesis,
    Score,
    Coding,                # a code + label (used for predicates)
    Agent,
)
```

Two enums used on packets live in `sieve.datamodel.sieve_models`:

```python
from sieve.datamodel.sieve_models import CurationStatus, DecisionType

CurationStatus.UNREVIEWED   # also ACCEPTED, REJECTED, CONTROVERSIAL
DecisionType.ACCEPT         # also REJECT, CONTROVERSIAL
```

An `EvidencePacket` requires an `id` and a `statement`; `status` defaults to
`UNREVIEWED` and `has_evidence_lines` defaults to an empty list:

```python
packet = EvidencePacket(
    id="pkt_000001",
    statement=SieveStatement(
        id="stmt_1",
        subject="MONDO:0004979",
        predicate=Coding(code="rdfs:subClassOf"),
        object="MONDO:0005275",
    ),
)
packet.status                       # CurationStatus.UNREVIEWED
packet.model_dump(exclude_none=True)
```

`CurationDecision` is the record written to the store's decision log:

```python
from datetime import datetime, timezone
from sieve.datamodel import CurationDecision, DecisionType

decision = CurationDecision(
    id="dec_1",
    packet_id="pkt_000001",
    curator="orcid:0000-0001-2345-6789",
    curator_name="Dr. Jane Smith",   # optional
    decision=DecisionType.ACCEPT,
    rationale="Strong concordance across sources.",  # optional
    certainty=0.9,                   # optional, 0–1
    decided_at=datetime.now(timezone.utc),
)
```

---

## sieve.datamodel.loaders

Evidence items are a polymorphic union; loading through the base class would
drop subclass fields. These loaders dispatch each item to its concrete class by
its `type` field before validating.

```python
from pathlib import Path
from sieve.datamodel.loaders import load_packet, packet_from_dict, EVIDENCE_ITEM_TYPES

def load_packet(path: Path) -> EvidencePacket        # load from a YAML file
def packet_from_dict(data: dict) -> EvidencePacket   # build from a raw dict
```

`EVIDENCE_ITEM_TYPES` is the `type` discriminator registry — a
`dict[str, type[BaseModel]]` mapping an item's `type` string to its class. It
includes both the concrete names (`"ConcordanceItem"`, `"AgentContribution"`,
`"ComputationalResult"`, `"SieveDocument"`, `"SieveDataItem"`,
`"SieveStudyResult"`) and the base-type aliases `"Document"`, `"DataItem"`,
`"StudyResult"`.

```python
packet = load_packet(Path("inbox/examples/asthma.yaml"))
packet = packet_from_dict({
    "id": "pkt_000001",
    "statement": {"subject": "MONDO:0004979",
                  "predicate": {"code": "rdfs:subClassOf"},
                  "object": "MONDO:0005275"},
    "has_evidence_lines": [
        {"direction_of_evidence_provided": "supports",
         "has_evidence_items": [{"type": "SieveDocument", "id": "d1", "pmid": "28884740"}]},
    ],
})
```

---

## sieve.store

`PacketStore` persists packets as full JSON plus a few promoted columns for
querying, alongside a decision log. The DuckDB file defaults to
`data/sieve.duckdb`; pass `":memory:"` for an ephemeral store.

```python
from sieve.store import PacketStore

class PacketStore:
    def __init__(self, db_path: str = "data/sieve.duckdb")

    def insert_packet(self, packet: EvidencePacket) -> str
    def get_packet(self, packet_id: str) -> EvidencePacket | None
    def list_packets(self, status: str | None = None) -> list[dict]
    def get_stats(self) -> dict[str, int]
    def update_status(self, packet_id: str, status: str) -> None
    def set_item_rating(self, packet_id: str, item_id: str, rating: str) -> None
    def get_decisions(self, packet_id: str) -> list[dict]
    def record_decision(self, decision: CurationDecision) -> str
    def close(self) -> None
```

Notes on behavior (from the source):

- `insert_packet` upserts by packet `id` (INSERT OR REPLACE) and returns the id.
  It computes and stores the Net Evidence Ratio into the `evidence_score`
  column.
- `get_packet` returns `None` if the id is unknown.
- `list_packets` returns dicts with keys `id`, `subject_id`, `predicate`,
  `object_id`, `status`, `evidence_score`.
- `get_stats` returns a `{status: count}` map.
- `update_status` and `set_item_rating` are no-ops if the packet id is unknown.
- `get_decisions` returns rows newest-first with keys `id`, `packet_id`,
  `curator`, `curator_name`, `decision`, `rationale`, `certainty`, `decided_at`.

```python
store = PacketStore(":memory:")
store.insert_packet(packet)
store.list_packets(status="UNREVIEWED")
store.get_stats()                      # e.g. {"UNREVIEWED": 1}
store.update_status("pkt_000001", "ACCEPTED")
store.set_item_rating("pkt_000001", "d1", "ACCEPTED")
store.record_decision(decision)
store.get_decisions("pkt_000001")
store.close()
```

---

## sieve.packet_ingest

Validate packet dicts against the LinkML schema and load YAML packets into a
`PacketStore`.

```python
from pathlib import Path
from sieve.packet_ingest import (
    validate_packet_dict,     # (data: dict) -> list   ([] means valid)
    ingest_packet_file,       # (path: Path, store: PacketStore) -> str
    ingest_packet_directory,  # (path: Path, store: PacketStore) -> dict
)
```

- `validate_packet_dict` returns a list of LinkML validation results; an empty
  list means the dict is valid against the `EvidencePacket` class.
- `ingest_packet_file` loads one YAML packet and inserts it, returning its id.
- `ingest_packet_directory` walks `**/*.yaml` and `**/*.yml`, ingesting each and
  collecting per-file errors. It returns
  `{"files": int, "success": int, "errors": int, "error_details": [...]}`.

```python
store = PacketStore(":memory:")
results = validate_packet_dict(packet.model_dump(mode="json", exclude_none=True))
if not results:
    stats = ingest_packet_directory(Path("inbox/examples/"), store)
    print(f"{stats['success']}/{stats['files']} ingested")
```

---

## sieve.packet_export

Serialize packets to YAML, and turn ACCEPTED / REJECTED / CONTROVERSIAL packets
into OWL axiom annotations (RDF). Serialization uses `serialize_as_any` so
polymorphic evidence items keep their subclass fields.

```python
from pathlib import Path
from rdflib import Graph
from sieve.packet_export import (
    packet_to_yaml,          # (packet: EvidencePacket) -> str
    export_packets_to_yaml,  # (packets: list[EvidencePacket], output_path: Path) -> None
    packet_to_rdf,           # (packet: EvidencePacket, graph: Graph | None = None) -> Graph
    export_packets_to_rdf,   # (packets, output_path=None, format="turtle") -> str
    expand_curie,            # (curie: str | None, converter) -> URIRef | None
    get_obo_converter,       # () -> curies.Converter
)
```

- `packet_to_rdf` only emits triples for packets whose status is one of
  `ACCEPTED`, `REJECTED`, `CONTROVERSIAL`; others are skipped with a warning and
  an (unchanged) graph is returned. Pass an existing `graph` to accumulate.
- `export_packets_to_rdf` builds one graph over all packets, serializes it in
  `format` (any rdflib format, e.g. `"turtle"`, `"xml"`, `"nt"`), optionally
  writes it to `output_path`, and returns the serialized string.

```python
graph = packet_to_rdf(packet)                     # empty unless packet is decided
turtle = export_packets_to_rdf([packet], Path("axioms.ttl"), format="turtle")

export_packets_to_yaml([packet], Path("out/packets.yaml"))
yaml_text = packet_to_yaml(packet)
```

---

## sieve.scoring

The **Net Evidence Ratio** (NER) reduces a packet's evidence lines to a single
number in `[-1, +1]`. Each line is weighted by its explicit
`score_of_evidence_provided`, else mapped from `strength_of_evidence_provided`
(`strong`=1.0, `moderate`=0.6, `weak`=0.3), else 1.0.

```python
from sieve.scoring import net_evidence_ratio, line_score

def net_evidence_ratio(packet: EvidencePacket) -> float   # (S+ - S-) / (S+ + S- + S0)
def line_score(line) -> float                             # weight of a single line
```

```python
ner = net_evidence_ratio(packet)   # +1 all supporting, -1 all disputing, 0 if empty
```

See the [primer](primer.md#from-evidence-to-a-score) for a worked example.

---

## sieve.auth

ORCID OAuth login and curator authorization for the Streamlit review UI. The
UI-rendering helpers depend on Streamlit session state; the checks below are the
parts useful outside a running app.

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

Authorized curators are read from `curators.yaml` (path overridable via the
`CURATORS_FILE` env var), cached for 60 seconds:

```yaml
curators:
  - orcid: "0000-0001-2345-6789"
    name: "Dr. Jane Smith"
    role: admin
  - orcid: "0000-0002-3456-7890"
    name: "Dr. John Doe"
    role: curator
```

```python
if is_authorized_curator("0000-0001-2345-6789"):
    role = get_curator_role("0000-0001-2345-6789")   # "admin"
```

Streamlit-bound helpers (`get_current_user`, `set_current_user`, `logout`,
`handle_oauth_callback`, `render_login_ui`) are used by the app and require an
active Streamlit session.
