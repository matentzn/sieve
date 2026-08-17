# How the three resources model evidence today

A side-by-side reading of the actual schemas, as background for the [SPEC](../SPEC.md) and the
[corpus](../examples/README.md). Everything here is as-built on 2026-08-13.

## At a glance

| | DisMech | MeDIC | mondo-ai / sieve |
|---|---|---|---|
| Schema | `src/dismech/schema/dismech.yaml` (~6k lines, ~200 classes) | `src/medic/schema/{evidence,provenance,indication,...}.yaml` | `schema/{minimal,sepio_classes,sieve}.yaml` |
| Core abstraction | flat `evidence:` list on almost any object | ordered transformation chain per mention | `EvidencePacket → EvidenceLine → items` |
| Question it answers | *what backs this claim?* | *how did this string become this ID?* | *should I believe this claim?* |
| Evidence item | `EvidenceItem` (reference, title, supports, source, snippet, explanation, images) | `EvidenceItem` (~30 slots) + `TextSpan` + `Mention` | 6 polymorphic subclasses of `SieveEvidenceItem` |
| Polarity | `EvidenceItemSupportEnum` (5 values, 3 concerns) | **none** | `EvidenceDirection` (supports/disputes/neutral) |
| Strength | folded into the support enum (`PARTIAL`) | `evidence.confidence` HIGH/MED/LOW + `source_role` | `EvidenceStrength` + `score_of_evidence_provided` |
| Study-kind axis | `EvidenceSourceEnum` (5 values) | `EvidenceSourceTypeEnum` (5) **and** `SourceTypeEnum` (5) — two parallel vocabularies | `EvidenceSource` in the kernel (6, ECO-bound) |
| Aggregation | none (prose + `MechanismConfidenceEnum`) | `reliability` tier + noisy-OR `PairConfidence` | `EvidenceSynthesis` + NER |
| Interpretation provenance | **none** | agent + agent_version + tool + tool_version per step | `CurationActivity` on synthesis only |
| Curation state | `Discussion.status`, `CurationStatusEnum` | `curation_status` on `research_list` only | `CurationStatus` + `CurationDecision` |
| Verbatim quote | `snippet`, validated exact against PubMed | `spans[].text` with `role` + char offsets | `SieveDocument.quote`, `SieveDataItem.value` |

## DisMech

The most *evidence-shaped* of the three, and the one whose vocabulary the microschema is
modelled on. An `EvidenceItem` is deliberately tiny and attachable anywhere — pathophysiology
nodes, causal edges, treatments, phenotypes, genetic factors, differential diagnoses,
environmental factors, discussions, mechanistic hypotheses, external assertions, findings. That
ubiquity is why `HasEvidenceLines` exists as a mixin in the kernel: DisMech's own containers must
survive.

```yaml
EvidenceItem:
  slots: [reference, reference_title, supports, evidence_source, snippet, explanation, images]
```

**What it gets right.** The `snippet` is machine-validated to be an exact excerpt from the cited
abstract (`linkml-reference-validator`), and ontology terms are validated against real
ontologies. DisMech evidence is therefore unusually *verifiable*, which matters more for an
AI-curated resource than for a human-curated one.

**The support enum conflates three concerns.**

| Value | Actually is |
|---|---|
| `SUPPORT` | direction |
| `REFUTE` | direction |
| `PARTIAL` | **strength** (weak/indirect support) |
| `NO_EVIDENCE` | **operational** — the cited reference does not mention the claim |
| `WRONG_STATEMENT` | **operational** — the annotated claim is factually wrong; the evidence documents the correct information |

The agreed split (SPEC §4.1): direction takes `SUPPORT`/`REFUTE`, `PARTIAL` becomes
`SUPPORTS` + `WEAK`, and the last two are QC signals that should cause the extracted claim to be
reviewed or dropped rather than persisting in released evidence. Note `WRONG_STATEMENT` in
particular targets the *claim*, not the snippet — it is a curation instruction wearing an
evidence value's clothes.

**No interpretation provenance at all.** DisMech is AI-curated and AI-maintained, with human
review as the PR gate, and its `explanation` field is an LLM's reasoning about why a snippet
supports a claim. Nothing records which model wrote it, when, or under which prompt/skill
version. Given that the stated adoption blocker for the clinical community is *visible
confidence and provenance*, this is the highest-value gap in the resource.

**Structures with no counterpart in either profile:** `mechanistic_hypotheses` with
`hypothesis_group_id` / `status` (CANONICAL / EMERGING / DEPRECATED) and edges tagged with the
groups they belong to (R19); `Discussion` with `kind` / `status` / `attaches_to` /
`proposed_experiments` (R15); `MechanismConfidenceEnum` (ESTABLISHED / PROVISIONAL /
HYPOTHETICAL) at the node level (R17).

## MeDIC

MeDIC's `evidence.yaml` says in its own header that it is *"inspired by dismech"*, and it shows:
`EvidenceSourceTypeEnum` is DisMech's/sieve's study-kind axis minus `EXPERT_CONSENSUS`, arrived
at independently. But the resemblance is superficial, because MeDIC's real model is in
`provenance.yaml`.

**The transformation chain.** Every mention carries a `resolution` with an ordered `pipeline` of
steps, each typed by `TransformationCategory` (EXTRACTION / TRANSLATION / GROUNDING /
NORMALIZATION) and `TransformationMethod` (LLM / DETERMINISTIC_RULE / LEXICAL_MATCH /
TRANSLITERATION / API / STRUCTURED_FIELD / SOURCE_ASSERTED / HUMAN), with input and output values
on every step (invariant I-8: `pipeline[n].output_value == pipeline[n+1].input_value`), a
`confidence` and a mandatory `confidence_basis`, and typed failure-mode flags.

Three properties follow: the chain is **monotone**, **mechanical** (no step is a judgement about
the world), and **replayable** from git-tracked SSSOM/Babelon decision stores. Nothing in it
argues the claim is true; it would look identical if the regulator had made a mistake.

**Two failure-mode vocabularies, correctly separated.** `ExtractionFlag` is strictly about
recognising the *entity* (`hallucination`, `truncated_snippet`, `coreference_ambiguity`,
`scope_narrowed`); `AssertionFlag` is about the *relation* (`negated_inversion`,
`over_extraction`, `wrong_section`, `wrong_pairing`). The canonical case: "hyperthyroidism" is
recognised perfectly, but the sentence lists it as a depleting condition, not an indication. This
separation is better than anything in the other two resources and worth propagating.

**`TextSpanRoleEnum` is the sleeper feature.** Every span is typed by its role in the document —
`SECTION_HEADER`, `SECTION_TEXT`, `SUBSECTION_HEADER`, `LIMITATION_STATEMENT`, `TABLE_CELL`,
`LIST_ITEM`… — so negation and entailment can be scoped to a span rather than to a concatenation
of a whole section. `LIMITATION_STATEMENT` in particular is exactly the REFUTES-shaped data
MeDIC then cannot express (M2).

**What it lacks.** No direction. No `Document` class (the document is a scattering of strings:
`setid`, `reference`, `source_document_url`, `regulatory_document_url`). No strength axis
distinct from chain confidence. `reliability` is a synthesis in effect but its reasoning lives
in `reliability.py`, not in the data. Two parallel evidence-kind vocabularies applied to
different products, one of whose descriptions ("the provenance/source of the evidence") writes
the conflation into the schema.

`medic/docs/sepio-sieve-alignment.md` is the authoritative analysis of all this and sets out a
five-stage adoption path (annotate → unify vocabulary → add evidence concepts → import kernel →
curation integration) with the recommendation to do stages 0–2 on MeDIC's own merits and hold
stages 3–4 until sieve's blockers close.

## mondo-ai / sieve

sieve owns the canonical model; mondo-ai currently carries a camelCase copy with `example.org`
URIs (blocker B3). The model is three files:

```
minimal.yaml       the promotable microschema — EvidencedClaim, EvidenceLine, EvidenceItem,
                   TextSpan, Document, HasEvidenceLines mixin; imports only linkml:types
sepio_classes.yaml the rest of SEPIO — Entity, InformationEntity, Statement, Proposition, Agent,
                   Contribution, Activity, StudyResult, + InformationEntityProvenance mixin
sieve.yaml         the curation model — EvidencePacket, SieveEvidenceLine, six item subclasses,
                   EvidenceSynthesis, CurationActivity, CurationDecision, Score
```

`sieve.yaml` imports both and its classes are `is_a` the kernel's plus mixins
(`InformationEntityProvenance`, `CuratedEvidence`), so **any minimal instance is a valid sieve
evidence item by reuse rather than parallel definition**. Semantics are carried by
`class_uri`/`slot_uri`, not by the LinkML `is_a` tree — which is why the kernel can be lean and
still be SEPIO.

**The six item subclasses** are `ConcordanceItem`, `SieveDocument`, `SieveDataItem`,
`SieveStudyResult`, `ComputationalResult`, `AgentContribution`. In production only
`ConcordanceItem` is used, at 165,818 instances.

**`AgentContribution` is the distinctive class**: `contributor` × `trust_level` (community /
domain_expert / curator / authority) × `channel` (issue_tracker / personal_communication /
direct_submission / public_forum) × `contribution_type` (suggestion / review / decision /
provision). Three orthogonal scoring dimensions on a contribution, which is the machinery the
vision's trust argument needs — except that `trust_level` is an enum, and what the vision
actually describes is a numeric, dated, attributed, revisable declaration by an organisation.

**mondo-ai is ahead of sieve on `TextMiningResult`** — the "C" shape (`extraction_score`,
`document_section`, `text_location`, `extraction_method`, all optional so "A stays valid") exists
in `mondo_ai_sieve.yaml` but not yet in this repo's `schema/minimal.yaml`, where it is phase 3 of the
07-31 spec. It should be promoted into the kernel, and MeDIC's structured character offsets
should go in with it.

## The one-paragraph summary

DisMech has the vocabulary and none of the provenance. MeDIC has the provenance and none of the
vocabulary. mondo-ai has both and no data that exercises either. The microschema is the shared
vocabulary all three can agree on; the SIEVE profile is where the calculus lives; and the three
things none of them can do — supersession, defeaters, source independence — are the ones to take
upstream to SEPIO rather than solve locally.
