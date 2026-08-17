# Migrating sieve onto the SEPIO/SIEVE evidence model

*Date: 2026-07-26*

## Problem

sieve has two data models that have drifted apart. The one *in this repo*
(`schema/curation_model.yaml`) is a flat, prototype-era model: a `CurationRecord`
with a flat `evidence[]` list of polymorphic `Evidence` subtypes. The one in
`../mondo-ai` (`sieve_sepio.yaml` + `sepio_classes.yaml`) is a properly
SEPIO-aligned model that was always intended to be *the* sieve model — its schema
files literally declare `id: https://w3id.org/sieve`. mondo-ai currently owns and
develops that model; sieve lags behind with the older shape.

This migration makes the SEPIO/SIEVE model canonical **in sieve**, and rebuilds
the whole sieve application (storage, ingest, validation, export, RDF export,
scoring, and the Streamlit UI) on top of it. mondo-ai will later import the model
from sieve, reversing today's copy direction.

Decisions taken during brainstorming (2026-07-26):

- **Scope: full migration.** Schema, generated models, DuckDB layer, ingest,
  export, RDF export, and the Streamlit UI all move to the new model.
- **sieve owns the canonical model.** `sepio_classes.yaml` + `sieve.yaml` become
  the source of truth here; mondo-ai imports them (its own follow-up).
- **Greenfield data.** Existing DuckDB/YAML data is disposable; no data-migration
  code. Example packets are rewritten in the new shape and re-ingested.
- **Keep four current-sieve features** (grafted onto the new model): per-item
  `rating`, the `CurationDecision` audit log, GitHub/tool provenance fields, and
  explicit `eco_code`/`eco_label`.
- **Explicit EvidenceLines.** Authors always structure evidence as
  `EvidenceLine`s containing items; no auto-wrapping of bare items.

## The two models, side by side

| Concern | Old sieve (`curation_model.yaml`) | New (SEPIO/SIEVE) |
|---|---|---|
| Container | `CurationRecord` | `EvidencePacket` (`tree_root`) |
| Assertion | `Assertion` (`subject_id`, `predicate`, `object_id`, labels, `display_text`) | `SieveStatement is_a` SEPIO `Statement` (`subject`, `predicate: Coding`, `object`, `subjectLabel`, `objectLabel`, `statementText`) |
| Evidence shape | flat `evidence[]` of `Evidence` subtypes | `hasEvidenceLines[]` → `SieveEvidenceLine` → `hasEvidenceItems[]` (two-level) |
| Evidence items | `ConcordanceEvidence`, `LiteratureEvidence`, `ExpertReviewEvidence`, `ComputationalEvidence` | `ConcordanceItem`, `SieveDocument`, `AgentContribution`, `ComputationalResult`, `SieveDataItem`, `SieveStudyResult` (all descend from SEPIO `InformationEntity`) |
| Provenance | `AssertionProvenance` class | SEPIO `InformationEntity` slots (`contributions`, `sources`, `dateAuthored`, `specifiedBy`) + `CurationActivity is_a Contribution` |
| Synthesis | `EvidenceSynthesis` (`summary`, `confidence`) | `EvidenceSynthesis` (`summary`, `score: Score`, `direction`, `cited_evidence`, `generated_by`) |
| Decisions | `CurationDecision` (separate table) | — (folded into `curated_by`) |
| Models | hand-written `models.py` | `gen-pydantic` from schema |

## Target design

### Schema layout

```
schema/
  sepio_classes.yaml   # SEPIO base — copied verbatim from mondo-ai (id: w3id.org/sepio-model)
  sieve.yaml           # canonical SIEVE model (id: w3id.org/sieve), imports sepio_classes
```

`schema/curation_model.yaml` is deleted. `mondo_ai_sieve.yaml` is **not** brought
in — it is mondo-ai pipeline-specific and stays there.

`sieve.yaml` is `sieve_sepio.yaml` renamed, plus the grafts below.

### Grafting the four kept features

**1 + 4 — per-item `rating` and explicit ECO, via one mixin.** The six evidence-item
classes branch under different SEPIO parents, so a shared base class is not
available. Define a mixin and apply it to all six:

```yaml
classes:
  CuratedEvidence:
    mixin: true
    description: >-
      Curation-workflow slots grafted onto every Sieve evidence item: a steward's
      per-item verdict and an explicit ECO hook.
    attributes:
      rating:
        range: CurationStatus
        description: The evidence steward's verdict on this individual evidence item.
      eco_code:
        range: uriorcurie
        description: Evidence & Conclusion Ontology (ECO) term for this item.
      eco_label:
        range: string
  # each of ConcordanceItem, AgentContribution, SieveDocument, SieveDataItem,
  # SieveStudyResult, ComputationalResult gains:  mixins: [CuratedEvidence]
```

`rdf_export` depends on `rating == ACCEPTED` to decide which item sources to emit,
so this graft is load-bearing, not cosmetic.

**2 — `CurationDecision` audit log.** Carried over as its own class + `DecisionType`
enum, stored in its own DuckDB table (a decision *history*, richer than a single
`curated_by`):

```yaml
  CurationDecision:
    description: A curator's decision on an EvidencePacket (one row per decision; keeps history).
    attributes:
      id: {identifier: true, range: string}
      packet_id: {range: uriorcurie, required: true, description: Reference to EvidencePacket.id}
      curator: {range: uriorcurie, required: true, description: Curator ORCID}
      curator_name: {range: string}
      decision: {range: DecisionType, required: true}
      rationale: {range: string, description: Explanation (required for rejections)}
      certainty: {range: float, minimum_value: 0, maximum_value: 1}
      decided_at: {range: datetime, required: true}
```

**3 — GitHub/tool provenance.** Add to `CurationActivity`: `pull_request`,
`issue`, `created_with` (e.g. a Protégé URI). Add `mappingSet` (SSSOM mapping-set
URI) to `ConcordanceItem`, complementing its existing `mappingJustification`.

### Dropped from old sieve (with rationale)

- `AssertionProvenance` class → its fields map onto SEPIO `InformationEntity`
  provenance slots (`contributions`, `sources`, `dateAuthored`) + `CurationActivity`.
- `SourceType` enum → `ConcordanceItem` already carries free-text `sourceName` +
  formal `sources`; the coarse enum adds nothing.
- `EvidenceType` enum → replaced by real polymorphism (`EvidenceItemType` +
  class identity).
- Old `EvidenceDirection` values (`SUPPORTS`/`CONTRADICTS`/`UNCERTAIN`) → adopt the
  new model's `supports`/`disputes`/`neutral`.

### Field mapping (old → new), for the migration of examples and I/O code

- `CurationRecord` → `EvidencePacket`; `status` → `status`; `created_at`/`updated_at`
  → packet `created`/`updated`. The base `EvidencePacket` has no `evidence_steward`
  or packet-level `confidence`: the steward is derived from
  `curated_by.contributor` (and promoted to a DuckDB column for filtering), and the
  old `confidence` maps to `CurationDecision.certainty` on the deciding record.
- `Assertion.subject_id/predicate/object_id` → `SieveStatement.subject/predicate
  (Coding: code=CURIE, label=predicate_label)/object`; `*_label` → `subjectLabel`/
  `objectLabel`; `display_text` → `statementText`.
- `LiteratureEvidence` → `SieveDocument` (`quoted_text`→`quote`,
  `quote_location`→`quoteLocation`, `publication_title`→`title`,
  `publication_id`→`pmid`/`doi`, `explanation`→ line-level or item `description`).
- `ExpertReviewEvidence` → `AgentContribution` (`reviewer_orcid`→`contributor`
  Agent id, `reviewer_name`→`Agent.name`, `reviewed_at`→`date`,
  `trustLevel`=`domain_expert`/`curator`, `contributionType`=`review`,
  `issue`→`reference`).
- `ComputationalEvidence` → `ComputationalResult` (`method`→`methodName`,
  `method_uri`→`methodId`, `parameters`→`parameters`, `confidence_score`→inherited
  `value`).
- `ConcordanceEvidence` → `ConcordanceItem` (source fields map 1:1; `mapping_set`→
  grafted `mappingSet`).
- Per-item `direction`/`evidence_strength` → line-level
  `directionOfEvidenceProvided`/`scoreOfEvidenceProvided`; item `rating`/`eco_*` →
  the `CuratedEvidence` mixin.

### Models — adopt `gen-pydantic`

Replace hand-written `src/sieve/models.py` with generated
`src/sieve/datamodel/sieve_models.py` plus `src/sieve/datamodel/loaders.py` for
polymorphic evidence-item deserialization (mirroring mondo-ai's `loaders.py`). Add
a `just gen-pydantic` recipe; exclude the generated file from mypy in `mypy.ini`.
This eliminates the schema/Pydantic drift risk recorded in `SPEC.md` §14.

### Storage — keep DuckDB, restructure

sieve remains a DuckDB + Streamlit review app.

- `evidence_packets` table: `id` (PK), promoted filter columns (`subject_id`,
  `predicate`, `object_id`, `status`, `evidence_score`, `evidence_steward`,
  `created`, `updated`), and `packet_json` holding the full serialized
  `EvidencePacket` (nested lines/items live here).
- `curation_decisions` table: as today, keyed to `packet_id`.
- **NER scoring** moves to operate over `hasEvidenceLines[]`:
  `NER = (S⁺ − S⁻) / (S⁺ + S⁻ + S⁰)` where the sums are over
  `scoreOfEvidenceProvided` grouped by `directionOfEvidenceProvided`.

### I/O components

- `ingest.py`: YAML → `EvidencePacket` (generated Pydantic + loaders) → store.
  Evidence must be authored as explicit `EvidenceLine`s.
- `validators.py`: validate against `schema/sieve.yaml`, target class
  `EvidencePacket`.
- `export.py`: `EvidencePacket` → YAML round-trip.
- `rdf_export.py`: `EvidencePacket` → `owl:Axiom` annotations. Reads
  `statement.subject/predicate/object`, walks `hasEvidenceLines → hasEvidenceItems`,
  emits sources for items with `rating == ACCEPTED`; SEPIO evidence reference and
  status-specific annotations preserved from the current implementation.
- `app.py`: render an `EvidencePacket` — statement, each `EvidenceLine` with its
  items rendered by type, per-item rating controls, decision recording.

## Testing strategy (TDD, per phase)

Every phase lands with `just test` (pytest + mypy + ruff) green, matching the CI
gate just brought to green.

- **Schema**: `gen-json-schema` / `gen-pydantic` succeed on `sieve.yaml`; valid
  fixture `EvidencePacket`s validate; counter-examples fail (e.g. bad
  `directionOfEvidenceProvided`, `rating` outside the enum).
- **Loaders**: a packet with one of each evidence-item type round-trips through
  `loaders.py` to the correct subclasses.
- **Storage**: insert/read a packet; promoted columns match the JSON; NER matches
  a hand-computed value.
- **Ingest/validate/export/RDF**: one real example packet (rewritten Antiphospholipid
  or asthma case) ingests, validates, exports to YAML, and produces the expected
  `owl:Axiom` triples with only `ACCEPTED` item sources.

## Phasing (one spec, phased implementation — each phase a green PR)

1. **Schema + generated models** — bring in `sepio_classes.yaml` + `sieve.yaml`,
   graft the `CuratedEvidence` mixin, `CurationDecision`, and provenance fields;
   wire `gen-pydantic` + `loaders.py`; schema/loader tests. Delete
   `curation_model.yaml` and `models.py`.
2. **Storage + ingest + validate** — DuckDB restructure, YAML→`EvidencePacket`
   ingest, validation, NER scoring, rewritten example packets.
3. **Export + RDF** — `export.py` and `rdf_export.py` on the new shape.
4. **Streamlit UI** — `app.py` renders and curates the new packet shape.

## Non-goals

- No changes to mondo-ai in this task beyond documenting the hand-off (mondo-ai
  re-pointing its imports at sieve, and w3id publishing, are separate follow-ups).
- No data-migration tooling (greenfield).
- No new storage backend (DuckDB stays; not adopting mondo-ai's JSONL+SQLite store).
- The full SEPIO surface in `sepio_classes_full.yaml` stays archived; only the
  trimmed `sepio_classes.yaml` is used.

## Hand-off to mondo-ai (follow-up, not this task)

Once sieve owns the model, mondo-ai's `mondo_ai_sieve.yaml` should import
`sieve.yaml`/`sepio_classes.yaml` from sieve (or a published `w3id.org/sieve`)
instead of keeping local copies, and the two repos' generated models should be
regenerated from the single source. Track as a separate issue.
