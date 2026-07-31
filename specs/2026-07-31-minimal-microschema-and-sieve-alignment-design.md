# Minimal evidence microschema + full sieve alignment

*Date: 2026-07-31*

## Problem

Two evidence models need to live in one repo and be **fully compatible**:

1. **The minimal microschema** — a small, importable "A + C" evidence model
   sketched by Matt Brush (SEPIO project). It is the model we want to *promote for
   adoption by all downstream projects*. It must be small, standalone, and
   pitchable on its own.
2. **The full sieve model** — the complex, fully SEPIO-aligned curation model
   (`EvidencePacket → EvidenceLine → evidence items`, plus concordance, agent
   contributions, synthesis, decisions, scoring). This stays sieve's primary model.

Today sieve has only #2, in camelCase, with placeholder `example.org/sepio-model`
class/slot URIs (no real SEPIO IRIs). The minimal model does not exist here yet.

The goal is that **any minimal-model instance is a valid sieve evidence item** —
achieved by *reuse*, not parallel definition: the shared classes are defined once,
in the minimal kernel, and sieve extends them.

### The "A" and "C" shapes

- **A** — a text span interpreted as evidence: a `value` (the quoted text) plus the
  `Document` it was `reported_in`. The minimal, always-valid form.
- **C** — a text-mining / LLM extraction result: everything A has, *plus* optional
  extraction provenance (score, document section, span location, method). Adopting C
  must not break A: with only `value` + `reported_in`, a C instance is
  indistinguishable from an A instance.

## Decisions (locked in brainstorming, 2026-07-31)

- **Snake_case flip.** sieve's slots are renamed camelCase → snake_case repo-wide, so
  sieve can `is_a` the (snake_case) minimal classes. This is the enabler for reuse.
- **Standalone lean kernel.** `minimal.yaml` imports only `linkml:types`. It is
  SEPIO-aligned by `class_uri` / `slot_uri` annotations, **not** by importing the
  SEPIO base. Lightest possible thing to adopt downstream.
- **Full re-base now.** The overlapping classes (`EvidenceLine`, the A/C items,
  `Document`) are defined once, in `minimal.yaml`. `sepio_classes.yaml` and
  `sieve.yaml` import the kernel and extend it; the duplicate definitions are removed
  from `sepio_classes.yaml`.
- **Reconcile, don't just map.** `document_type`↔`subtype` and `evidence_source`↔ECO
  are unified via enum `meaning:` IRIs (below), not left as prose mappings.
- **C reuses A's slots.** `TextMiningResult is_a TextSpan`; it does **not** introduce
  the parallel `supporting_text` / `supporting_document` vocabulary from Matt's Alt
  block.

## Architecture

Three schema files, dependency arrows pointing at the kernel:

```
                    minimal.yaml          (imports: linkml:types only)
                    ─────────────         the promotable microschema
                    EvidenceLine          class_uri/slot_uri → sepio:/ECO:
                    EvidenceItem (abstract)
                    TextSpan          (A)
                    TextMiningResult  (C)  is_a TextSpan
                    Document
                    enums: Direction, EvidenceSource, DocumentType
                       ▲                        ▲
             imports   │                        │   imports
              ┌────────┘                        └────────┐
   sepio_classes.yaml                              sieve.yaml
   ────────────────                                ─────────
   the rest of SEPIO:                              full curation model:
   Entity, InformationEntity,                      SieveEvidenceLine is_a EvidenceLine
   Statement, Proposition, Agent,                  Sieve items   is_a TextSpan / TextMiningResult
   Contribution, Activity,                         + mixins: [InformationEntityProvenance,
   StudyResult, DataSet, utilities                            CuratedEvidence]
   + InformationEntityProvenance (mixin)           EvidencePacket, ConcordanceItem,
                                                    AgentContribution, ComputationalResult,
                                                    EvidenceSynthesis, CurationActivity,
                                                    CurationDecision, scoring, ...
```

`sieve.yaml` imports **both** `minimal.yaml` and `sepio_classes.yaml`.

### Why a provenance mixin

sieve's evidence items currently inherit SEPIO `InformationEntity` provenance
(`contributions`, `sources`, `date_authored`, `specified_by`, `is_about`,
`derived_from`, `record_metadata`) through the deep `Entity → InformationEntity →
DataItem/Document/EvidenceLine` chain. A lean kernel cannot carry that chain and stay
adoptable. So:

- `minimal.yaml` classes are lean and flat (each pinned to its SEPIO `class_uri`).
- `sepio_classes.yaml` defines an `InformationEntityProvenance` **mixin** holding those
  provenance slots.
- sieve's rich evidence classes are `is_a` the minimal class **and**
  `mixins: [InformationEntityProvenance, CuratedEvidence]`.

Net: minimal stays small; sieve keeps every slot it has today; RDF/SEPIO semantics are
preserved because `class_uri`/`slot_uri` (not the LinkML `is_a` tree) carry the
semantics. This is *stronger* than today, where URIs are `example.org` placeholders.

## The minimal kernel (`minimal.yaml`)

Classes (all lean; `class_uri` shown):

| Class | `class_uri` | Key slots |
|---|---|---|
| `EvidenceLine` | `sepio:EvidenceLine` | `has_evidence_items[]`, `direction_of_evidence_provided` (Direction), `evidence_source` (EvidenceSource), `description` |
| `EvidenceItem` *(abstract)* | `sepio:InformationEntity` | `id`, `reported_in` (Document), `description` |
| `TextSpan` **(A)** | `sepio:DataItem` | `is_a EvidenceItem`; `value` (the span text) |
| `TextMiningResult` **(C)** | `sepio:DataItem` (+ text-mining subtype) | `is_a TextSpan`; `extraction_score` (0–1), `document_section`, `text_location`, `extraction_method` — **all optional** |
| `Document` | `sepio:Document` | `id`, `title`, `document_type` (DocumentType) |

Plus a `HasEvidenceLines` mixin (provides the `has_evidence_lines` slot) so hosts —
sieve's `EvidencePacket`, dismech's disease record, etc. — graft the evidence
structure onto their own container without the kernel imposing one.

Enums (each permissible value carries a `meaning:` IRI — this is the reconciliation
mechanism):

- **`Direction`** — superset from the 07-12 spec's `SupportDirection`
  (`SUPPORTS`, `REFUTES`, `PARTIAL`, `NO_EVIDENCE`, `WRONG_STATEMENT`, `UNCERTAIN`),
  `meaning:` → SEPIO direction terms where they exist.
- **`EvidenceSource`** — `HUMAN_CLINICAL`, `MODEL_ORGANISM`, `IN_VITRO`,
  `COMPUTATIONAL`, `EXPERT_CONSENSUS`, `OTHER`; each `meaning:` → the corresponding
  **ECO** branch term.
- **`DocumentType`** — `PRIMARY_LITERATURE`, `REVIEW`, `PREPRINT`,
  `DATABASE_RECORD`, `OTHER`; each `meaning:` → its publication-type IRI.

### A-validity, concretely

`TextMiningResult`'s only inherited required slot is `TextSpan.value`. Every
extraction slot is optional. Therefore a `TextMiningResult` with just `value` +
`reported_in` validates identically to a `TextSpan`. "Create C so that A stays valid"
is satisfied structurally, not by convention.

## The two reconciliations

### R1 — `document_type` (enum) ↔ `Document.subtype` (Coding)

A `DocumentType` enum value *is* a compact `Coding`: `code` = the PV's `meaning`
IRI, `label` = the PV text, `system` = the vocabulary. sieve's `Document` keeps
`subtype: Coding` for the long tail **and** reuses the kernel's `document_type` slot
for the common case. A minimal instance (`document_type: PRIMARY_LITERATURE`) is valid
in sieve and round-trips losslessly to a `Coding`.

### R2 — `evidence_source` ↔ per-item `eco_code`

These are the **same vocabulary (ECO) at two granularities**, not two unrelated axes:
- `evidence_source` — coarse, **line-level**, enum-bound-to-ECO (the "kind of study").
- `eco_code` — precise, **item-level**, any ECO term.

Both slots remain, but the vocabulary is unified through the `EvidenceSource`
`meaning:` IRIs. (This refines the 07-12 D3 "keep them separate" call: separate
*slots/levels*, one *vocabulary*.)

## Phasing (one spec, four green steps)

Each phase ends with `just test` green (pytest + mypy + ruff) and clean
`gen-pydantic` / `gen-json-schema`.

1. **Snake_case flip.** Rename every slot in `sepio_classes.yaml` + `sieve.yaml` to
   snake_case; pin real `slot_uri:` where a SEPIO predicate exists; keep the `date`
   slot's range as `string` (the gen-pydantic/Py3.10 guard). Regenerate
   `sieve_models.py`; update the 5 hand-written modules, 6 test files, YAML fixtures,
   and `docs/primer.md`. No behaviour change.
2. **Extract the kernel.** Create `minimal.yaml` with `EvidenceLine`, `EvidenceItem`,
   `TextSpan`, `Document`, enums (with `meaning:` IRIs), and the `HasEvidenceLines`
   mixin. Remove the overlapping classes from `sepio_classes.yaml`; add its
   `InformationEntityProvenance` mixin. Re-point sieve's classes to `is_a` the kernel
   + mixins. Prove a minimal instance validates standalone and as a sieve item.
3. **Add C (`TextMiningResult`).** Add it to `minimal.yaml` (`is_a TextSpan`), to
   `loaders.py` polymorphic dispatch, and to the `EvidenceItemType` enum. Fixtures:
   the *same* evidence in A-form and C-form both validate; loaders round-trip C.
4. **Evidence-source axis + reconciliations.** Add `evidence_source` to
   `EvidenceLine`; wire R1 (`document_type` on `Document`) and R2 (ECO `meaning:`s).
   Fixtures cover a line with `evidence_source: HUMAN_CLINICAL`; a bad value fails.

## Migration inventory (phase 1 surface)

- **Schema:** `schema/sepio_classes.yaml`, `schema/sieve.yaml`.
- **Generated (auto):** `src/sieve/datamodel/sieve_models.py` via `just gen-pydantic`.
- **Hand-written code (~20 refs):** `app.py` (7), `scoring.py` (5),
  `datamodel/loaders.py` (3), `packet_export.py` (3), `store.py` (2).
- **Tests (~25 refs):** `test_scoring.py` (9), `test_store.py` (6),
  `test_loaders.py` (4), `test_packet_export_rdf.py` (3), `test_example_packet.py` (2),
  `test_packet_export_yaml.py` (1).
- **Fixtures:** `tests/data/valid/`, `tests/data/invalid/`.
- **Docs:** `docs/primer.md` (13).

## Testing strategy (TDD)

- **Kernel standalone:** valid/invalid fixtures for `EvidenceLine` + A + C validate /
  fail against `minimal.yaml` alone (proves it's adoptable with zero sieve deps).
- **Compatibility:** a minimal A instance and a minimal C instance both validate as
  sieve evidence items inside an `EvidencePacket` (proves reuse/compatibility).
- **Reconciliation:** `document_type: PRIMARY_LITERATURE` validates and maps to the
  expected `Coding`; `evidence_source: HUMAN_CLINICAL` carries the expected ECO
  `meaning:`.
- **Regression:** the full existing suite stays green after the flip; a stale
  camelCase key now fails validation.

## Blockers / open questions

- **B1 — Kernel home / id.** Proposed `id: https://w3id.org/sepio/minimal`
  (SEPIO-framework-aligned, since it is SEPIO's minimal model), authored in the sieve
  repo now, graduating to a registered w3id later (mirrors 07-12 D4). *Confirm the id
  before phase 2* — it is baked into every downstream import.
- **B2 — Real `meaning:` IRIs.** R1/R2 need actual ECO and publication-type CURIEs.
  Coarse ECO branch terms for `EvidenceSource` and publication-type IRIs for
  `DocumentType` must be looked up (OLS) during phase 4, not invented.
- **B3 — mondo-ai divergence.** Flipping the base to snake_case + real SEPIO URIs
  diverges from mondo-ai's camelCase/`example.org` copy. Intended (sieve owns the
  model per the 07-26 migration); mondo-ai inherits it when it re-points its import.
  Tracked as the existing mondo-ai hand-off follow-up.
- **B4 — `rdf_export` predicate URIs.** Verify `rdf_export` reads Python attributes
  (safe under rename) rather than the old `example.org` URIs before phase 1 lands.

## Non-goals

- No dismech example wired into sieve's tests (chose "C + axis", not the e2e).
- No data migration (greenfield, per the 07-26 spec).
- No mondo-ai changes here beyond documenting the hand-off.
- No w3id registration in this task (B1 graduation is a follow-up).
- Structured character offsets on `TextMiningResult` stay a single `text_location`
  string for now; a structured span type is a future extension.
