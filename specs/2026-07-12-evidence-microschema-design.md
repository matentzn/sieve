# Evidence Microschema: a shared, importable LinkML evidence model

*Date: 2026-07-12*

## Problem

Dozens of projects are emerging that describe their data in LinkML, each with its
own schema. Many of them independently model the same thing — **evidence that
supports or contradicts a claim** — and each reinvents it slightly differently.
We want one shared evidence model that any project can *import and reuse*, so that
"evidence" means the same thing (same slots, same enums, same ECO hooks) across the
ecosystem.

Two concrete existing models bracket the design:

- **dismech** (`src/dismech/schema/dismech.yaml`) has a flat `EvidenceItem`:
  `reference` (PMID), `reference_title`, `supports` (enum), `evidence_source`
  (enum), `snippet`, `explanation`, `images`. `evidence` is a
  `multivalued / inlined_as_list` slot reused across ~8 classes. It already uses
  `implements: linkml:authoritative_reference` and `linkml:excerpt`, and validates
  records at runtime with `linkml.validator.Validator`.
- **sieve** (`schema/curation_model.yaml`) has a richer, polymorphic hierarchy:
  abstract `Evidence` + `ConcordanceEvidence` / `LiteratureEvidence` /
  `ExpertReviewEvidence` / `ComputationalEvidence`, with `direction`
  (SUPPORTS/CONTRADICTS/UNCERTAIN), `evidence_strength` (0–1), `eco_code`, `rating`,
  and a separate `EvidenceSynthesis`.

The key observation: dismech's `EvidenceItem` and sieve's `LiteratureEvidence` are
nearly the same shape (reference + snippet + support-direction + explanation). A
shared **flat core** covers both. Where they differ — dismech's `evidence_source`
(clinical / in-vitro / …) versus sieve's `evidence_type` (concordance / literature /
…) — the two are *different axes* ("what kind of study produced it" vs "what kind of
evidence artifact it is") and must stay separate, not be collapsed.

## Goal and acceptance criteria

Deliver a shared evidence microschema **and prove it works** against dismech. The
proof-of-concept is complete when:

1. **Imported** — dismech's schema `imports:` the shared evidence module instead of
   defining its own `EvidenceItem`/enums, and the merged schema resolves.
2. **LinkML handles it** — `gen-project` / `gen-json-schema` / `gen-python` run on
   the merged dismech schema without error (dismech generates Python dataclasses, so
   `gen-python` must still succeed).
3. **A real record converts and validates** — at least one real dismech
   evidence-bearing record is converted to the shared shape and validates against the
   shared `EvidenceItem` via `linkml-validate`; and a record using the *old* enum
   value fails, proving the shared enum is actually enforced.

Bonus (proves the "shared" claim, not required for sign-off): validate a sieve
`LiteratureEvidence`-style record against the same shared `EvidenceItem`.

## Design decisions

These were open questions; the calls made here are what the spec commits to. Each is
flagged so it can be overturned at review.

### D1 — Conformance approach: plain importable module, lightly annotated (hybrid)

The shared model is a **plain LinkML module** — a single `.yaml` with classes, slots,
and enums that other schemas `imports:` and reuse by literal slot/class identity. We
do **not** adopt the full LinkML Microschema Profile machinery that
`linkml-microschemas-envar` uses (`instantiates: MicroschemaDefinition`, per-slot
`implements`/`exact_mappings` to an "anatomy", tier system, completeness checker).

Rationale: the profile machinery exists to *reconcile independently-authored schemas
that use different slot names after the fact*. Our goal is the opposite — one model
that everyone imports, so slot names are shared by construction and there is nothing to
reconcile. Building the anatomy/tier/checker layer now would solve a problem we've
designed away (YAGNI).

We keep the door open by **sprinkling `implements:` annotations** on the slots where a
standard LinkML meta-slot exists (dismech already does this: `authoritative_reference`,
`excerpt`). That is enough for a future project that *cannot* import the module to
declare conformance, without us building the full profile now.

### D2 — Shape: a flat `EvidenceItem` core; projects extend by subclassing

The shared module ships a **flat** `EvidenceItem` that is the superset-common-denominator
of dismech and sieve's literature evidence. It does **not** port sieve's polymorphic
subtypes. Projects that need more specialise via LinkML inheritance:

```yaml
# sieve, later:
imports:
  - https://w3id.org/linkml/microschemas/evidence
classes:
  LiteratureEvidence:
    is_a: EvidenceItem            # inherits the shared core
    slots: [quoted_text, quote_location, ...]   # sieve-specific extras
```

An `EvidenceItemMixin` (same slots, `mixin: true`) is also shipped for schemas that
want to graft the evidence slots onto an existing class rather than use `EvidenceItem`
as a range.

sieve-specific constructs (`ConcordanceEvidence`, `EvidenceSynthesis`, `rating`,
`designates_type`) stay in sieve. They are out of scope for the shared core.

### D3 — Vocabulary reconciliation

**Support direction.** Canonical slot `direction`, range `SupportDirection`, a superset
of both projects' vocabularies:

| Shared `SupportDirection` | dismech `supports` | sieve `direction` |
|---|---|---|
| `SUPPORTS`        | `SUPPORT`         | `SUPPORTS`     |
| `REFUTES`         | `REFUTE`          | `CONTRADICTS`  |
| `PARTIAL`         | `PARTIAL`         | —              |
| `NO_EVIDENCE`     | `NO_EVIDENCE`     | —              |
| `WRONG_STATEMENT` | `WRONG_STATEMENT` | —              |
| `UNCERTAIN`       | —                 | `UNCERTAIN`    |

The slot is named `direction` (not dismech's `supports`) because its values include
`REFUTES` — "supports" as a name whose value can be "refutes" is misleading. Cost:
dismech's data migration renames the `supports` slot → `direction` and rewrites enum
values (`SUPPORT`→`SUPPORTS`, `REFUTE`→`REFUTES`). This rename is mechanical and is
exactly the kind of conversion the proof-of-concept demonstrates on one record.
*Alternative if the data-churn cost is judged too high: keep the slot named `supports`
and add `aliases: [direction]`. Flagged for review.*

**Strength.** Optional `strength` slot (float, 0–1), from sieve's `evidence_strength`.
Optional/recommended so dismech records (which omit it) stay valid.

**Evidence source.** `evidence_source` slot, range `EvidenceSource`, taken from dismech
1:1 (`HUMAN_CLINICAL`, `MODEL_ORGANISM`, `IN_VITRO`, `COMPUTATIONAL`, `OTHER`) plus
`EXPERT_CONSENSUS`. This is the "what kind of study" axis and maps naturally onto ECO
branches.

**ECO hook.** `eco_code` (uriorcurie) + optional `eco_label`, the cross-domain standard
handle both projects already reference.

sieve's `evidence_type` discriminator (`CONCORDANCE`/`LITERATURE`/…) is **not** in the
core; it is a sieve subtype discriminator and stays in sieve (D2).

### D4 — Home of the module

Durable home: a **standalone repo** `linkml-microschemas-evidence`, sibling to
`linkml-microschemas-envar`, published at `https://w3id.org/linkml/microschemas/evidence`.
A standalone home is what makes reuse-across-projects clean: dismech importing evidence
from *sieve* would create a wrong dependency (dismech → sieve).

Interim (for this spec's PoC, since we're iterating here in sieve): author the module at
`microschemas/evidence.yaml` in the sieve repo, with the explicit intent to graduate it
to the standalone repo + w3id once validated. The PoC imports it by **local path via a
LinkML importmap** (reproducible offline / in CI); the **URL import** is the production
mechanism and is already proven — `linkml-microschemas-envar` imports the Microschema
Profile from a raw GitHub URL exactly this way.

## The shared module (`evidence.yaml`)

```yaml
id: https://w3id.org/linkml/microschemas/evidence
name: evidence
title: Evidence Microschema
description: >-
  A small, importable LinkML module for describing evidence that supports or
  contradicts a claim. Designed to be imported by many independent LinkML
  schemas so they share one evidence vocabulary.
license: MIT

prefixes:
  linkml: https://w3id.org/linkml/
  evidence: https://w3id.org/linkml/microschemas/evidence/
  ECO: http://purl.obolibrary.org/obo/ECO_
  PMID: http://www.ncbi.nlm.nih.gov/pubmed/
  DOI: https://doi.org/
  dcterms: http://purl.org/dc/terms/
default_range: string
default_prefix: evidence
imports:
  - linkml:types

classes:
  EvidenceItem:
    description: A single piece of evidence bearing on a claim.
    class_uri: evidence:EvidenceItem
    slots:
      - reference
      - reference_title
      - direction
      - strength
      - evidence_source
      - eco_code
      - eco_label
      - snippet
      - explanation
      - images

  EvidenceItemMixin:
    description: >-
      Mixin form of EvidenceItem, for schemas that graft evidence slots onto an
      existing class instead of using EvidenceItem as a range.
    mixin: true
    slots:
      - reference
      - reference_title
      - direction
      - strength
      - evidence_source
      - eco_code
      - eco_label
      - snippet
      - explanation
      - images

slots:
  reference:
    description: Authoritative reference/citation for this evidence (publication, database record, URL).
    range: uriorcurie
    implements:
      - linkml:authoritative_reference
    examples:
      - value: PMID:35533128
  reference_title:
    description: Human-readable title of the reference.
    range: string
    recommended: true
  direction:
    description: Whether the evidence supports, refutes, or is neutral toward the claim.
    range: SupportDirection
  strength:
    description: Optional strength/confidence of the evidence, 0 (weak) to 1 (strong).
    range: float
    minimum_value: 0
    maximum_value: 1
  evidence_source:
    description: The kind of study or observation that produced the evidence.
    range: EvidenceSource
  eco_code:
    description: Evidence & Conclusion Ontology (ECO) term classifying the evidence.
    range: uriorcurie
    examples:
      - value: ECO:0000269
  eco_label:
    description: Human-readable label of the ECO term.
    range: string
  snippet:
    description: Verbatim excerpt from the reference that supports or refutes the claim.
    range: string
    implements:
      - linkml:excerpt
  explanation:
    description: Free-text explanation of how the evidence bears on the claim.
    range: string
  images:
    description: Relative paths to supporting image artifacts.
    range: string
    multivalued: true

enums:
  SupportDirection:
    description: Polarity of an evidence item toward a claim.
    permissible_values:
      SUPPORTS:        {description: The evidence supports the claim.}
      REFUTES:         {description: The evidence contradicts the claim.}
      PARTIAL:         {description: The evidence partially or indirectly supports the claim.}
      NO_EVIDENCE:     {description: The reference contains no evidence relevant to the claim.}
      WRONG_STATEMENT: {description: The claim contains a demonstrable factual error; the evidence documents the correct information.}
      UNCERTAIN:       {description: Direction is uncertain or neutral.}
  EvidenceSource:
    description: The kind of study/observation producing the evidence.
    permissible_values:
      HUMAN_CLINICAL:   {description: Human clinical observations (patients, cohorts, case reports, trials, epidemiology).}
      MODEL_ORGANISM:   {description: In vivo animal evidence.}
      IN_VITRO:         {description: In vitro / ex vivo assays.}
      COMPUTATIONAL:    {description: In silico / modelling / ML studies.}
      EXPERT_CONSENSUS: {description: Expert consensus without primary data.}
      OTHER:            {description: Evidence not fitting the above.}
```

## How dismech consumes it

dismech's schema drops its local `EvidenceItem`, `EvidenceItemSupportEnum`, and
`EvidenceSourceEnum`, and instead:

```yaml
# dismech.yaml
imports:
  - linkml:types
  - evidence            # resolved to microschemas/evidence.yaml via importmap (PoC) / URL (prod)
slots:
  evidence:
    multivalued: true
    range: EvidenceItem  # now the shared class
    inlined_as_list: true
    recommended: true
```

Its ~8 evidence-bearing classes are unaffected — they reference the `evidence` slot,
whose range now points at the shared class. `supports` → `direction` is the one slot
rename that touches data.

## Testing strategy (TDD)

Both repos use LinkML validation + pytest; follow test-first.

**In the evidence module (destined for its own repo, envar-style):**
- `tests/data/valid/` — minimal and full `EvidenceItem` records that must validate.
- `tests/data/invalid/` — counter-examples that must fail (e.g., `direction: SUPPORT`
  — the old dismech spelling — must be rejected; `strength: 1.5` must be rejected).
- A schema test asserting the module compiles (`gen-project`) and that
  `EvidenceItem`/`EvidenceItemMixin` expose the expected slots.

**In dismech (the migration proof):**
- A test asserting the merged schema loads and `gen-python` succeeds.
- Convert one real record — the Antiphospholipid `has_subtypes` evidence list from
  `tests/data/valid/Disease-Antiphospholipid_Syndrome.yaml` (all `supports: SUPPORT`) —
  with a small converter (`supports`→`direction`, `SUPPORT`→`SUPPORTS`), and assert it
  validates against the shared `EvidenceItem`.
- Assert the *un*converted record (still `SUPPORT`) fails validation, proving the shared
  enum is enforced end to end.

## Non-goals

- No completeness checker, tier system, or Microschema-Profile anatomy (D1).
- No port of sieve's polymorphic subtypes or `EvidenceSynthesis` into the shared core (D2).
- Not migrating all of dismech's data or all ~8 consumer classes in the PoC — one record
  is the acceptance bar. Full data migration is a follow-up once the shape is approved.
- The pattern-generated evidence type noted in `todo.md` (DOSDP-generated statements) is
  a candidate future `EvidenceSource`/`evidence_type` value, not part of this PoC.

## Sequencing

1. Author `microschemas/evidence.yaml` + its valid/invalid fixtures and schema test (TDD).
2. Prove it stands alone: `gen-project` / `linkml-validate` fixtures green.
3. Wire dismech: importmap + schema edits; prove `gen-python` on merged schema.
4. Convert one dismech record + validation tests (both the passing and the failing case).
5. Bonus: validate a sieve literature record against the shared class.
6. On approval, graduate the module to `linkml-microschemas-evidence` + w3id, and open a
   follow-up for the full dismech data migration.
