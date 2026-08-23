# Monarch Evidence — Specification

**Status:** draft · **Date:** 2026-08-15 (rev. 2; §3.2, §7.1–7.3, R23–R26, Q8–Q10) · **Author:** Nico Matentzoglu
**Implementation:** this repo — [`schema/minimal.yaml`](../schema/minimal.yaml), [`schema/sieve.yaml`](../schema/sieve.yaml), [`transform/`](../transform)
**Corpus:** [`examples/`](examples/README.md) — 9 real records from DisMech, MeDIC and mondo-ai

> This document is written *from* the notes in the `~/ws/notes/evidence` thinking repo
> (`background/evidence_team_slack.md`, `background/evidence_scratchpad.md`,
> `docs/monarch-hackathon-evidence-briefing.md`), the sieve design specs in `../specs/`, and
> `medic/docs/sepio-sieve-alignment.md`. It states what I currently
> understand the plan to be. Where the notes are thin or I have inferred, that is flagged
> **[inferred]**. Where a decision is genuinely open it is in §10, not silently resolved.

---

## 1. Purpose

Monarch produces evidence in at least five places and models it five different ways. Naming
them, because "five ways" is not informative on its own:

| Place | How it models evidence | What it cannot say | Surveyed |
|---|---|---|---|
| **DisMech** | a flat `evidence:` list on 56 classes; one `supports` enum conflating direction, strength and QC | who did the interpreting, despite being AI-curated | yes, D1 to D3 |
| **MeDIC** | transformation chains and source assertions, provenance to a high standard | direction: there is no slot, only an implicit SUPPORTS | yes, M1 to M3 |
| **mondo-ai / sieve** | SEPIO packets with lines, items and synthesis | anything but agreement, so the aggregate is 1.0 across all 160,187 packets | yes, N1 to N3 |
| **Mondo** | a bare list of source CURIEs: 67,085 bracketed synonym sources and 165,813 `{source=...}` xref axiom annotations in `mondo-edit.obo` (counted 2026-08-17) | direction, strength, agent, date; none of them exist | counted, not in the corpus |
| **Monarch KG** | Biolink associations; the `begets` and nearest-source pattern | **not surveyed** | no, out of scope per §2 |

None of the five can currently express the one thing every downstream consumer asks for: *how
strongly, and in which direction, does the evidence bear on this claim, and who decided that?*

This spec defines **one semantic foundation with two profiles**:

| | Track 1: the microschema | Track 2: SEPIO Monarch |
|---|---|---|
| Name | `sepio-minimal` (`https://w3id.org/sepio/minimal`, PROVISIONAL) | the SIEVE profile (`https://w3id.org/sieve`) |
| Audience | *every* Monarch resource | projects that need evidence calculus |
| Size | 5 classes, 4 enums, importable, zero deps beyond `linkml:types` | ~20 classes, full SEPIO provenance |
| Shape | flat list of lines, each line a direction + a few text spans | lines with contributions, synthesis, curation state, scoring |
| Home | `../schema/minimal.yaml` | `../schema/sieve.yaml` + `../schema/sepio_classes.yaml` |
| Status | drafted, provisional id and `meaning:` IRIs | implemented, in production use by mondo-ai |

Both are **SEPIO Profiles of one Core Information Model**, connected by an explicit
[linkml-map](https://linkml.io/linkml-map/) transform, so a resource can start simple and lift
later without re-modelling. This mirrors how SEPIO itself is designed: flat and normalised
representations are both first-class, and map to each other.

**Gatekeeper constraint (Chris, via the hackathon briefing):** for the microschema to be
adopted across Monarch it has to be *simple and intuitive*. Optimise Track 1 for adoption
first; every slot must earn its place.

**Second constraint, no overfitting.** No class in either profile may be shaped around one
pipeline's output. The corpus exists to enforce this: a slot proposed by a single resource has
to be checked against the other eight records before it enters the kernel. The failure mode is
concrete: `EvidenceSource: OTHER` is already doing duty as "review article" in DisMech (D1)
because the axis was fitted to study kinds alone.

## 2. Scope

**In scope:** the shared evidence vocabulary; the two profiles; the mapping between them; the
adoption path for DisMech, MeDIC, mondo-ai/sieve and Mondo; the requirements the corpus proves
are real.

**Out of scope:** the curation UI; the scoring *policy* (which weights, which thresholds — that
is per-project governance, not schema); the Monarch KG's Biolink representation (we note the
`begets` / nearest-source pattern as prior art but do not specify it here); registering the
w3id.

## 3. The core axis

SEPIO's normalised backbone, and the thing everything else hangs off:

```
Statement          "Cystic fibrosis has_pathophysiology CFTR dysfunction"
   │                the claim being made
   │ has_evidence_lines
   ▼
EvidenceLine       "this item strongly supports the claim"
   │                an ARGUMENT — the result of an agent interpreting items as evidence.
   │                Carries direction, strength, and the provenance of the INTERPRETATION.
   │ has_evidence_items
   ▼
EvidenceItem       the thing interpreted as evidence
   │                exists independently of being interpreted; carries its OWN provenance
   │                (who produced it), and may be reused as evidence for other claims.
   │                A DataItem when it has a `value` (a text span is the common case);
   │                see §4.5 for the kinds that are not DataItems.
   │ reported_in    (when the item came from a document at all)
   ▼
Document           the publication or record the item was reported in
```

**`EvidenceItem` here is the role, not a class** (§3.1). The node is drawn abstract on purpose:
§4.4 shows that only four of twenty evidence kinds are a text span, and §4.5 concludes that
`has_evidence_items` has to range over the abstract role rather than a concrete text class.
Earlier drafts of this diagram called the node a `DataItem` and glossed it as *the span of text
itself*, which is true of the majority case and false of concordance, measurement, attestation
and testimony. For the same reason arrow 1 in §7.1 is *acquisition*, not *extraction*:
extraction is what it is for text-derived items only.

Three things follow, and they are the whole reason the nesting exists (Matt Brush, Slack
2026-08; scratchpad):

1. **Two provenances, not one.** Provenance on the *item* says "this data item was created by
   A, B, C". Provenance on the *line* says "I, agent X, on date D, following guideline G,
   interpreted these items as weakly supporting the claim". Collapsing item into line loses the
   second, which is precisely the axis Monarch needs for AI curation.
2. **Items are reusable.** The same text span can be evidence for one claim and against
   another. Making it an object rather than a field is what allows that.
3. **Lines may be heterogeneous.** Lumping several different kinds of evidence item under one
   direction and strength is *fine* and within SEPIO — an `EvidenceLine` is a line of
   reasoning, not a sentence. Split lines only when the reasoning genuinely differs.

**Counter-pressure, recorded honestly** (Sierra Moxon, Slack): the extra nesting is real cost —
Python classes and validators get deeper, and data creators can misuse the freedom in ways that
produce inconsistency. In practice it is often *cheaper to mint a new item than to find and
reuse an existing one*, so item reuse may stay theoretical (see R8 and D1 in the corpus, where
DisMech does duplicate rather than reuse). The answer is not to abandon the axis but to (a)
keep Track 1 flat enough that the nesting is invisible to adopters, and (b) publish grouping
guidance so pipelines produce consistent line granularity.

### 3.1 DataItem vs EvidenceItem

Recurring source of confusion, so stated plainly: **`EvidenceItem` is a *role*, not a class.**
Anything that is an information content entity can play it — a text span, a study result, a
dataset, a computational result, a curator's contribution. `DataItem` *is* a class, and a text
span is a `DataItem` with a `value` (the quoted text) and a `reported_in` (the document).
SEPIO subclasses further only when a use case needs it. (Gemini's "EvidenceItem is a legacy
bundled term" answer is wrong; ignore it.)

### 3.2 The statement is structured, and it lives in the host

The diagram above starts at `Statement`, which invites the reading that the kernel owns the
claim. It does not, and should not. **In every real host the statement is already structured,
and the kernel's job is to attach to it, not to restate it.**

Two host shapes, both real:

```yaml
# association style — the statement IS a triple
indication:
  subject: CHEBI:748790
  predicate: RO:0002606
  object: MONDO:0005148
  has_evidence_lines: [...]

# attribute style — the predicate is a slot on a record about the subject
drug:
  id: CHEBI:748790
  indication: MONDO:0005148
  evidence_indication: [...]      # sibling slot, because the attribute is a scalar
```

**All three shapes already validate against `minimal.yaml` unchanged** (verified 2026-08-15):
the association-style host via the `HasEvidenceLines` mixin, the attribute-style host by
declaring its own slot with `range: EvidenceLine`, and an `EvidencedClaim` carrying no
`statement_text` at all. The mixin is a convenience for the single-attachment case, **not the
only path** — a host with three independently evidenced attributes declares three slots. That
is not written down anywhere, and it should be, because the obvious reading of §4 is that the
mixin is the mechanism.

Two things the corpus makes plain:

- **`statement_text` is always generated.** Not one of the nine `statement_text` values appears
  in any source document. `exenatide is indicated for type 2 diabetes mellitus` (M1) is a
  rendering of `medic:CHEBI_748790--INDICATION--MONDO_0005148` — the triple is *in the id*.
  `"Lisch epithelial corneal dystrophy has exact synonym 'LECD'"` (N1, N3) renders an
  attribute assertion. This is the point requirements.md §4 was reaching for: the statement is
  almost never explicit in prose; what is explicit is the grounded structured form.
  So `statement_text` is a **label for humans, not a span** — and it sits one slot away from
  `TextSpan.value`, which *is* a verbatim span. That collision is a live misreading risk.
- **D1 had to invent a slot.** Its `minimal:` block carries
  `_host: mechanistic_hypotheses[canonical_variant_ttr_amyloidogenesis]` — a non-schema key,
  because there is no way to say *which* host node a claim belongs to. Where the host cannot
  nest (an external index, a review queue, a transform output), the attachment point has to be
  expressible. **[inferred]** the cheapest fix is one optional `about: uriorcurie` on
  `EvidencedClaim`, pointing at the host statement; the structured triple then lives where it
  already lives, in the host.

### 3.3 Conformance is not convergence

Sierra Moxon built [nine valid SEPIO encodings](https://gist.github.com/sierra-moxon/8513375c4ee89c53794cba67bbef340c)
of one claim (metformin indicated for type 2 diabetes) with identical evidence. All nine pass
`linkml-validate`, and nothing in the data says which convention was used. Four axes of choice:

1. `hasEvidenceFromSources`, `hasEvidence`, or `hasEvidenceLines`.
2. One pooled line, or one line per item.
3. Where pipeline steps go: nested evidence, component items, result rows, or contributions.
4. Where confidence attaches. Six slots accept it.

She also found the validator blind spot: when a slot's range is `InformationEntity`, LinkML emits
a JSON Schema `anyOf`, so an object matching the permissive parent passes even with required
child fields missing. `designates_type: true` on `Entity.type` fixes it. Independently hit in
§7.3 on 2026-08-16, where polymorphic inlining under `derived_from` validated for the same
wrong reason. Two people finding it separately is a good sign it is worth fixing.

**Her three questions, answered with what is measurable here.**

**Can the same statement and evidence produce different validated output?** Yes, and this repo
is already an instance. The `dismech_to_minimal` transform silently picks one convention, one
item becomes one line, in a single `expr`. That choice is her file 04, it is not written down
anywhere as a choice, and it is the reason 38 of 39 lines in the corpus have exactly one item.

**Does it matter?** Yes, and it is measurable. D2 has eight evidence items on one claim, three
supporting and five refuting. Net Evidence Ratio over the same eight items, under four
defensible conventions (computed 2026-08-17):

| Convention | Lines | NER |
|---|---|---|
| One line per item (her file 04, what sieve does today) | 8 | **−0.250** |
| Pool by direction (her file 03) | 2 | **0.000** |
| Group by direction and document | 5 | **−0.200** |
| The Q1 rule: direction + strength + source + document | 6 | **0.000** |

Same claim, same evidence, four numbers, two of them on opposite sides of zero. A consumer
applying a threshold at 0 gets "refuted on balance" or "perfectly balanced" depending only on
how the producer grouped. So yes: an agent reading one rendering rather than another would draw
a different conclusion about direction and strength, without any curated judgement having
changed.

Worse, the Q1 rule applied mechanically merges the three REFUTES lines from PMID:26745718 into
one, and the corpus notes at D2 say that is wrong, because they are three logically distinct
arguments. **Our own stated grouping rule destroys real structure on our own worked example.**
Q1 is not a documentation gap, it is an unsolved problem.

**Does a linkml-map transform help?** In one direction. Per-item to pooled is mechanical
aggregation. Pooled to per-item is not, because per-item directions were never authored and
cannot be invented. This is the same asymmetry as flat to nested: a transform moves shape, not
judgement. So a transform can normalise a producer's output *downward* to a coarser convention,
which is useful for consumers, and cannot repair a producer that chose too coarse a convention
in the first place. Declaring the convention costs one annotation. Recovering it later costs a
re-curation.

**What follows.** A profile that does not pin its convention has not narrowed SEPIO in the way
that matters. The pinning has to be machine-checkable, not prose in a spec, or producers will
diverge exactly as ClinGen's older dialect has (`evidenceLine` vs `hasEvidenceLines`, no
`DataItem` objects, strength in free-text comments).

### 3.4 The minimum useful record, and whether there is too much evidence

Sierra's other question: what is the *minimum* SEPIO-conformant output that captures the
evidence, given that an agent can produce an unbounded amount of trace, and that few humans will
read it.

The minimum that carries this corpus is already measured. Track 1 is five classes, and nine of
the fourteen `minimal:` blocks validate against it untouched; the five failures are two proposed
enum values, not missing structure (§4.4 and the corpus test). So the floor is roughly:
a statement, a direction, and one item with a `value` and a `reported_in`.

The volume question is new to this spec and it is a real one:

- mondo-ai holds **165,818 evidence items across 160,187 packets, and every packet is
  UNREVIEWED**. Nobody has read any of it. That is the empirical answer to "will humans digest
  agent output" as things stand.
- MeDIC's four-step transformation chain is larger than the claim it supports, and under §7 none
  of it is evidence.
- The corpus already notes that R18 has never been exercised, so the claim that trust
  accumulates across many weak interpretations is untested against data.

The two-track design is, unintentionally, an answer to this: **Track 1 is the reading surface
and Track 2 is the trace.** If that is the intent it should be stated, because it changes what
Track 1 is for. It stops being only an adoption ramp and becomes the thing a human or an agent
reads when it does not want the full record. That reframing is cheap and it makes the "start
simple, lift later" story stronger, since lifting no longer means the simple view goes away.

What is genuinely not answered: whether more trace is better, worse or merely more expensive.
Nobody has measured an agent's verdict quality against trace depth. See Q14.

## 4. Track 1 — the minimal microschema

Current draft: [`../schema/minimal.yaml`](../schema/minimal.yaml). Five classes, four enums, imports only
`linkml:types`. SEPIO-aligned by `class_uri`/`slot_uri` annotation, **not** by importing SEPIO
— so instances are semantically SEPIO evidence without dragging in the model.

| Class | `class_uri` | Key slots |
|---|---|---|
| `EvidencedClaim` | `sepio:Statement` | `id`, `statement_text`, `has_evidence_lines[]` |
| `EvidenceLine` | `sepio:EvidenceLine` | `direction_of_evidence_provided`, `strength_of_evidence_provided`, `evidence_source`, `description`, `has_evidence_items[]` |
| `EvidenceItem` *(abstract)* | `sepio:InformationEntity` | `id`, `reported_in`, `description` |
| `TextSpan` — shape **A** | `sepio:DataItem` | `is_a EvidenceItem`; `value` (required) |
| `Document` | `sepio:Document` | `id`, `title`, `document_type` |
| `HasEvidenceLines` *(mixin)* | — | grafts `has_evidence_lines` onto a host's own container |

Enums: `Direction` (`SUPPORTS`/`REFUTES`/`NEUTRAL`), `Strength`
(`STRONG`/`MODERATE`/`WEAK`), `EvidenceSource`
(`HUMAN_CLINICAL`/`MODEL_ORGANISM`/`IN_VITRO`/`COMPUTATIONAL`/`EXPERT_CONSENSUS`/`OTHER`, each
mapping onto an ECO branch), `DocumentType`.

### 4.1 Three splits that are load-bearing

- **Direction is polarity ONLY.** DisMech's `EvidenceItemSupportEnum` conflates three concerns
  into one slot. The split, agreed with Matt: `SUPPORT`/`REFUTE` → `direction`; `PARTIAL` →
  `direction: SUPPORTS` **plus** `strength: WEAK` (partial support is a strength, not a
  direction); `NO_EVIDENCE` and `WRONG_STATEMENT` are **operational/QC signals** that should
  cause the extracted claim to be reviewed or dropped, and must not persist in released
  evidence data.
- **Strength ≠ direction.** A separate qualitative scale, refinable later by item-level scores.
- **Evidence source ≠ document type.** "What kind of study" (`EvidenceSource`, coarse ECO) and
  "what kind of document" (`DocumentType`) are different axes. Per-item `eco_code` is the same
  ECO vocabulary at finer granularity — separate *slots and levels*, one *vocabulary*.

### 4.2 The "A" and "C" shapes

- **A** — a text span: `value` + `reported_in: Document`. The always-valid minimal item.
- **C** — a text-mining / LLM extraction result: everything A has plus *optional* extraction
  provenance (`extraction_score`, `document_section`, `text_location`, `extraction_method`).
  `TextMiningResult is_a TextSpan`, so with only `value` + `reported_in` a C instance validates
  identically to an A instance. C does **not** introduce a parallel
  `supporting_text`/`supporting_document` vocabulary.

C is currently implemented in `mondo-ai/src/mondo_ai/schema/mondo_ai_sieve.yaml` but **not yet
in `../schema/minimal.yaml`** — it is phase 3 of the 07-31 sieve spec. The corpus (M2, M3)
shows MeDIC needs structured character offsets on C, which the 07-31 spec deliberately
deferred to a single `text_location` string.

C is also where the ordered grounding chain lands — see §7.3 for R26's resolution and why it
does not belong on SEPIO's native provenance slots.

### 4.3 What the microschema deliberately does not have

No `Agent`, no `Contribution`, no curation status, no synthesis, no scoring, no item identity
beyond an optional `id`. A resource that needs any of those is on Track 2 for that part of its
model. Keeping them out is what makes Track 1 pitchable.

**Open tension** (§10, Q3): the corpus shows that *interpretation provenance* — who read this
span as supporting the claim, and with which model — is exactly what makes AI-curated evidence
trustworthy, and it is on the Track 2 side of the line. DisMech is AI-curated and today records
none of it. If Track 1 stays agent-free, every AI-curated resource has to reach into Track 2
immediately, which weakens the "start simple" story.

### 4.4 Every kind of evidence in the three repositories

Surveyed 2026-08-16 across `dismech.yaml`, MeDIC's `schema/*.yaml`, `mondo_ai_sieve.yaml` and
`sieve.yaml`, plus the nine-record corpus. Counts are measured where a store exists.

| # | Kind of evidence | Where it lives today | Volume | Has a span? |
|---|---|---|---|---|
| 1 | Verbatim span from a publication | dismech `EvidenceItem.snippet` + `reference`; mondo-ai PubMed enrichment | 79,042 (dismech disorders) | yes |
| 2 | Verbatim span from a regulatory document | MeDIC label statements (DailyMed, EMA, PMDA, CDSCO, GRLS) | ~9,700 rows | yes |
| 3 | Value read from a structured field or database record | MeDIC `STRUCTURED_FIELD`; ontology records (N1) | in 2 and 4 | a field value, not prose |
| 4 | Cross-source concordance | mondo-ai `ConcordanceItem` | 165,818 items | **no** |
| 5 | Study result or statistic | dismech `AssociationStatistics`, `Prevalence`, `GeneCaseFraction`; SEPIO `StudyResult` | per-record | no, a number |
| 6 | Clinical trial outcome | dismech `ClinicalTrial`; MeDIC `ResearchPhaseEnum`, `StudyStatusEnum` | per-record | sometimes |
| 7 | Model organism observation | dismech `AnimalModel`, `ExperimentalModel`, `ModelMechanismLink` | per-record | no |
| 8 | In vitro or ex vivo assay result | dismech `Experiment`, `ExperimentalReadout`, `Biochemical` | per-record | no |
| 9 | Computational or in silico result | dismech `ComputationalModel`; sieve `ComputationalResult` | per-record | no, a score |
| 10 | Text-mining or LLM extraction result | mondo-ai `TextMiningResult` (shape C); MeDIC `EXTRACTION` step | store-wide | yes, plus how it was obtained |
| 11 | Entity grounding or mapping step | MeDIC `GROUNDING`/`NORMALIZATION`; SSSOM justifications | every MeDIC row | no |
| 12a | Expert testimony, no retrievable basis | sieve `AgentContribution`; mondo-ai ORCID lines | per-record | no, the assertion *is* the datum |
| 12b | Expert determination over evidence | dismech `Discussion` kinds `INTERPRETATION`, `CONTROVERSY` | per-record | no, cites other items |
| 13 | Organisational or consortium decision | mondo-ai consortium lines, `trust_level: authority` | store-wide | no |
| 14 | Regulatory approval as attestation | MeDIC `approvals` (authority, status, date) | ~9,700 | no |
| 15 | External assertion from another curated resource | dismech `ExternalAssertion`, ClinGen classifications | per-record | no |
| 16 | AI synthesis over a whole packet | mondo-ai `EvidenceSynthesis`, `RecommendedAction` | store-wide | no |
| 17 | Expert review of existing evidence | sieve `AgentContribution`; dismech `Discussion` kinds `INTERPRETATION`, `HUMAN_MODEL_MISMATCH` | per-record | no |
| 18 | Absence of evidence (a source checked, nothing found) | nowhere | N1 needs it for a denominator | n/a |
| 19 | Image or figure artefact | dismech `EvidenceItem.images` | 9 | no |
| 20 | Pattern-derived assertion (DOSDP and similar) | nowhere | wanted, see `todo.md` | no |

Two readings of this table matter.

**Only kinds 1, 2, 3 and 10 have a span.** They are also the overwhelming majority of the volume.
Everything else is a record, a number, a mapping, or a judgement. A kernel whose only concrete
item class is a text span forces the other sixteen kinds to invent a quote, which is the N1
finding generalised.

**Kinds 12, 13, 16 and 17 are not items at all.** They are interpretation acts: an agent read
something and reached a verdict. Under §3 and §7.1 that is what an `EvidenceLine` is. Modelling
them as items puts the agent on the wrong side of arrow 2.

### 4.5 The item taxonomy [PROPOSED]

Two groups, kept visibly separate because they carry different obligations.

**SEPIO conceptual classes.** Reused, never redefined. Monarch does not own these and should not
rename them.

| Class | Role |
|---|---|
| `InformationEntity` | the abstract root; playing the *EvidenceItem role* means being one of these |
| `DataItem` | a discrete acquired datum, carries `value` |
| `Document` | the publication or record an item is `reported_in` |
| `StudyResult` | data items from one study about one focus |
| `Statement`, `EvidenceLine` | the claim, and the argument bearing on it |
| `Contribution`, `Agent` | who did what, when (Track 2) |

**Monarch extension classes.** New, owned here, each annotated with a SEPIO `class_uri` so
instances stay SEPIO-valid.

| Class | `class_uri` | Covers | Shape |
|---|---|---|---|
| `TextDerivedEvidenceItem` | `sepio:DataItem` | kinds 1, 2, 3, 10 | `value` (required) + `reported_in` + optional extraction provenance + optional ordered `grounding` chain |
| `ConcordanceEvidenceItem` | `sepio:InformationEntity` | kind 4 | source subject/predicate/object + `mapping_justification`; **no `value`** |
| `MeasurementEvidenceItem` | `sepio:StudyResult` | kinds 5, 6, 7, 8 | a focus, a result, a study kind |
| `ComputationalEvidenceItem` | `sepio:DataItem` | kind 9 | method, parameters, software version, a score |
| `AttestationEvidenceItem` | `sepio:InformationEntity` | kinds 14, 15 | an authority, a status, a date; a third party asserting the claim |
| `TestimonyEvidenceItem` | `sepio:DataItem` | kind 12a | `value` (what was asserted) + `asserted_by` + `traceability`; `reported_in` optional |

**`TextDerivedEvidenceItem` replaces `TextSpan`.** The name says what the thing is, which
`TextSpan` does not, and it reads better to adopters than SEPIO's `DataItem` or Matt's
`StudyResult` / NER-result framing. **The rename costs nothing semantically:** `class_uri` stays
`sepio:DataItem`, so instances are the same SEPIO evidence they were before. This is a naming
decision in the profile, not a divergence from the core model. It also absorbs shape C: the
extraction slots are optional, so an instance with only `value` and `reported_in` is shape A.

#### Expert opinion and evidence synthesis are not the same thing

An earlier draft of this section folded both into "expert review is a line". That is wrong, and
the difference is the one that matters most for scoring.

**Evidence synthesis is always an evaluation of concrete pieces of evidence.** It is
second-order: its inputs are other items or lines, it carries `cited_evidence`, and it is
defeated by attacking those inputs. N3's LLM verdict and D2's needed verdict over 3 supporting
and 5 refuting items are both this.

**Expert opinion need not rest on anything retrievable.** A clinician of twenty years asserts
"A is a treatment for B". They may not be able to say which paper taught them, and there may be
no paper. It is first-order evidence, and it is defeated by attacking the expert's standing or
reliability, not by attacking cited inputs, because there are none.

ECO already draws this line, in two different branches (IRIs checked against OLS 2026-08-17):

| | Evidence synthesis | Expert review of evidence | Expert opinion (testimony) |
|---|---|---|---|
| Inputs | other items or lines | other items or lines | none required |
| Order | second | second | **first** |
| Warrant | the cited evidence and the method | the cited evidence and the expert | the expert's standing alone |
| Defeated by | attacking the inputs | attacking the inputs | attacking the expert |
| ECO branch | inferential: `ECO:0000205` curator inference, `ECO:0000001` inference from background scientific knowledge | same | documented statement: `ECO:0006151` → `ECO:0000204` author statement |
| Model as | `EvidenceSynthesis` (T2) | `EvidenceLine` with items, `interpreted_by` | `EvidenceLine` over a `TestimonyEvidenceItem` |

**The operational rule: if it cites evidence it is a synthesis, if it does not it is testimony.**
That is checkable rather than a matter of judgement, and it decides which slot the number goes
in. A synthesis score is computed over inputs. A testimony's weight comes from `TrustLevel` on
the asserting agent, which is R12.

**This closes Q11.** The earlier worry was that expert review with nothing underneath produces a
line with zero items. It does not, because **the testimony is itself the item**. An assertion is
a real information artefact: it has a value (what was said), an author, and sometimes a document
(a guideline, a meeting record, a personal communication). Every line keeps at least one item and
the kernel needs no zero-item special case.

The axis that matters on a `TestimonyEvidenceItem` is whether the assertion can be followed back
to anything, which is `StatementTraceability` in §4.6. ECO's `ECO:0000034`, *author statement
without traceable support*, is exactly the twenty-years-of-practice case, and it has been an
annotation code since the GO NAS/TAS days. Treating it as evidence with a declared weight is
established practice, not an invention here.

Consequence for §4.4: kind 12 splits into **12a expert testimony** (first-order, an item) and
**12b expert determination over evidence** (second-order, a line or a synthesis). Kinds 16 and 17
are second-order and stay lines. Kind 13, the organisational inclusion decision, remains
provenance under the §7 test and is not evidence at all.

**`has_evidence_items` must range over the abstract `EvidenceItem`**, not over a concrete text
class. This is the change `issues/issue_kernel_item_range.md` already asks for, and the table in
§4.4 is the general argument for it.

### 4.6 Shared enums

The vocabulary both tracks agree on. `T1` ships in the microschema, `T2` in the SIEVE profile,
`C` on shape C only.

| Enum | Track | Values |
|---|---|---|
| `Direction` | T1 | `SUPPORTS`, `REFUTES`, `NEUTRAL` |
| `Strength` | T1 | `STRONG`, `MODERATE`, `WEAK` |
| `EvidenceSource` | T1 | `HUMAN_CLINICAL`, `MODEL_ORGANISM`, `IN_VITRO`, `COMPUTATIONAL`, `EXPERT_CONSENSUS`, `REGULATORY` *(proposed, Q7)*, `OTHER` |
| `DocumentType` | T1 | `PRIMARY_LITERATURE`, `REVIEW`, `PREPRINT`, `DATABASE_RECORD`, `REGULATORY_LABEL` *(proposed, Q7)*, `GUIDELINE` *(proposed)*, `OTHER` |
| `EvidenceItemType` | T1 | `TEXT_DERIVED`, `CONCORDANCE`, `MEASUREMENT`, `COMPUTATIONAL`, `ATTESTATION`, `TESTIMONY` |
| `ConfidenceBasis` | T1 | `MEASURED`, `DETERMINISTIC`, `PRIOR`, `SELF_REPORTED` |
| `StatementTraceability` | T1 | `TRACEABLE` (`ECO:0000033`), `CLINICAL_STUDY_REFERENCED` (`ECO:0006016`), `UNTRACEABLE` (`ECO:0000034`) |
| `GroupingConvention` | T1 | `ONE_LINE_PER_ITEM`, `POOLED_BY_DIRECTION`, `BY_DIRECTION_AND_DOCUMENT`, `BY_REASONING` (§3.3, R27) |
| `SpanRole` | C | `SECTION_HEADER`, `SECTION_TEXT`, `LIMITATION_STATEMENT`, `TABLE_CELL`, `LIST_ITEM`, `STRUCTURED_FIELD`, `DOCUMENT_TITLE`, `UNKNOWN` |
| `GroundingStepCategory` | C | `EXTRACTION`, `TRANSLATION`, `GROUNDING`, `NORMALIZATION` |
| `TrustLevel` | T2 | `community`, `domain_expert`, `curator`, `authority` |
| `CurationStatus` | T2 | `UNREVIEWED`, `ACCEPTED`, `REJECTED`, `CONTROVERSIAL` |
| `ContributionType` | T2 | `suggestion`, `review`, `decision`, `provision` |
| `ContributionChannel` | T2 | `issue_tracker`, `personal_communication`, `direct_submission`, `public_forum` |

Provenance of the borrowed ones: `ConfidenceBasis` is MeDIC's, extended here with
`SELF_REPORTED` so N3's number can be labelled for what it is. `SpanRole` is a condensation of
MeDIC's twelve-value `TextSpanRoleEnum`. `TrustLevel`, `ContributionType` and
`ContributionChannel` are sieve's as they stand.

`StatementTraceability` is the only enum here whose `meaning:` IRIs are **confirmed** rather than
pending: all three were checked against OLS on 2026-08-17 and their ECO definitions match the
intended sense. That is a small piece of blocker B2 closed, and it suggests the way to close the
rest is to look for the branch ECO already has instead of proposing values first.

One gap this exposes: `EvidenceSource` has `EXPERT_CONSENSUS`, which is a *group* reaching
agreement. Individual testimony is a different thing and currently has nowhere to go. Either add
`EXPERT_TESTIMONY` or accept that the `EvidenceItemType: TESTIMONY` plus `StatementTraceability`
pair already says it, and leave the source axis alone. **Undecided.**

Deliberately **not** shared: MeDIC's `TransformationMethod`, `ExtractionFlag`,
`GroundingQualityEnum` and the other arrow-1 vocabularies (they are pipeline-specific and belong
in MeDIC), and dismech's `MechanismConfidenceEnum` (R17, still contested).

## 5. Track 2 — SEPIO Monarch (the SIEVE profile)

Implemented in [`../schema/sieve.yaml`](../schema/sieve.yaml), imports both `minimal.yaml` and the trimmed
`sepio_classes.yaml`, and adds:

```
EvidencePacket
├── statement: SieveStatement                   is_a sepio:Statement
├── has_evidence_lines: [SieveEvidenceLine]     is_a minimal:EvidenceLine
│     └── has_evidence_items: polymorphic —
│           ConcordanceItem | SieveDocument | SieveDataItem |
│           SieveStudyResult | ComputationalResult | AgentContribution
├── evidence_synthesis: EvidenceSynthesis       (summary, Score, direction, cited_evidence,
│                                                generated_by: CurationActivity)
├── curated_by: CurationActivity                is_a sepio:Contribution
├── status: CurationStatus                      UNREVIEWED | ACCEPTED | REJECTED | CONTROVERSIAL
└── decisions (separate table): CurationDecision (curator, rationale, certainty, timestamp)
```

Distinctive features, all exercised by the corpus:

- **`AgentContribution`** — a contribution *as an evidence item*, with the orthogonal scoring
  dimensions `trust_level` (community / domain_expert / curator / authority) × `channel` ×
  `contribution_type`. This is where "ORG trusts Opus at 65% and Sonnet at 56%" lives: not as a
  model's self-reported confidence, but as the curating organisation's declared trust in an
  interpreter, revisable over time.
- **`CuratedEvidence` mixin** — per-item `rating` + explicit `eco_code`/`eco_label`.
- **`EvidenceSynthesis` + `Score`** — an *inspectable* aggregation. Net Evidence Ratio
  `(S⁺ − S⁻)/(S⁺ + S⁻ + S⁰)` over lines is the current default; the point is that the
  reasoning is a first-class object, not buried in a scoring script.
- **`InformationEntityProvenance` mixin** — the SEPIO provenance slots (`contributions`,
  `sources`, `date_authored`, `specified_by`, `derived_from`, `record_metadata`) mixed in
  rather than inherited, so the kernel stays lean.

## 6. The bridge

`minimal.yaml` is the shared kernel; `sieve.yaml` classes `is_a` the kernel classes plus
mixins. Reuse, not parallel definition — **any minimal instance is a valid sieve evidence
item**. Two linkml-map transforms already exist and are tested end-to-end
(`just transform-all` from the repo root):

```
DisMech record ──dismech_to_minimal──▶ minimal EvidencedClaim ──minimal_to_sieve──▶ sieve EvidencePacket
```

The reference walkthrough is the Fanconi Anemia "Hematopoietic Stem Cell Attrition" node
([`../docs/monarch-evidence.md`](../docs/monarch-evidence.md)).

## 7. Evidence vs provenance vs data quality

The single most consequential distinction in this spec, taken from
`medic/docs/sepio-sieve-alignment.md` §3, which I adopt wholesale. There are **three**
concepts, not two:

| | Question | Territory |
|---|---|---|
| **Provenance** | Where did this *record* come from and how was it produced? | W3C PROV; MeDIC's transformation chain |
| **Evidence** | What are the reasons to believe or disbelieve the *claim*? | SEPIO; has polarity and weight |
| **Data quality** | How faithfully does this record represent its source? | the derivative of provenance |

Test for classifying any field:

1. Does it survive if the claim turns out to be false? → **provenance**.
2. Would it change if a different pipeline produced an identical record? → **provenance or
   data quality**, never evidence.
3. Would a domain expert who trusts your pipeline completely still want to see it? →
   **evidence**.

**The consequence that matters most:** every confidence number MeDIC computes today is a
data-quality number. `0.855` on the gemifloxacin record means "we are 85.5% confident we linked
the right CHEBI id", not "there is an 85.5% chance the claim is true". Mapping chain confidence
onto `score_of_evidence_provided` would silently convert "unsure of the identifier" into "weak
evidence for the treatment". **Chain confidence is a gate on the line, never the line's score.**

Corollary for the whole programme: a resource may be *excellent* at provenance and have *no*
evidence model (MeDIC), or have a rich evidence vocabulary and almost no interpretation
provenance (DisMech). These are different gaps and need different work.

### 7.1 Where each one attaches

The three concepts are not three layers. They attach at different places on the core axis, and
the important move is this: **evidence and provenance attach to the nodes; quality attaches to
the arrows.**

```
Statement            evidence is ABOUT this, and only this
    ▲
    │  ARROW 2 — interpretation:  "does this item bear on that claim, and how?"
    │     quality here    = was the reading correct?          N3, R11, R12
    │     provenance here = who read it, when, under which guideline/model
    │
EvidenceLine         evidence LIVES here: direction + strength, relative to a named target
    ▲
    │  has_evidence_items
    │
EvidenceItem         provenance here = which agent/tool/version produced this item
    ▲
    │  ARROW 1 — acquisition:  "does this item faithfully represent its source?"
    │     quality here    = scope narrowing, grounding fidelity, chain    M2, M3
    │
Document
```

Read off it:

- **Evidence is a property of the line, never of the item.** D3 makes this unavoidable: one
  human-genetics span is REFUTES against the ADSA mechanism claim and *supports* the
  discussion's own conclusion. Direction is only meaningful relative to a named target, so it
  cannot live on the item.
- **There are two provenances** (§3 point 1), on the two nodes, and they answer different
  questions.
- **There are two qualities**, on the two arrows, and *they are different numbers*:

| | Arrow 1 — acquisition fidelity | Arrow 2 — interpretation correctness |
|---|---|---|
| Question | did we faithfully get this item out of its source? | was reading this item as bearing on the claim correct? |
| Corpus | M2 (scope narrowing), M3 (four-step chain, 0.855) | N3 (LLM self-reported 0.95), N2 |
| Governed by | provenance / the pipeline | R11 interpretation provenance + R12 declared agent trust |
| MeDIC has | ✓✓ best in class | ✗ no interpretation step exists |
| DisMech has | ✓ (validated exact snippets) | ✗ despite being AI-curated |

This is where a terminology divergence needs settling. MeDIC's §3 — which the table above adopts
wholesale — defines data quality as *"how faithfully does this record represent its source"*,
which is **arrow 1**. The working definition in `../requirements.md` is *"how likely is it that
the supporting evidence was interpreted correctly"*, which is **arrow 2**. Both are real, both
are needed, and conflating them is how M2 happens: every arrow-1 step scores 1.0, the record's
`reliability` is HIGH, the composition is still wrong, and arrow 2 was never assessed because
MeDIC has no interpretation act to assess.

**The rule that follows, and it is the same rule twice.** Neither quality number may be written
into `strength_of_evidence_provided` or a line `Score`. §7's existing formulation — *chain
confidence is a gate on the line, never the line's score* — is the arrow-1 version. The arrow-2
version is R12: what belongs on the line is the **organisation's declared, dated, revisable
trust in the interpreter**, not the interpreter's opinion of itself. N3 currently stores the
latter in a slot shaped like the former, which is the single most consequential defect in the
corpus.

### 7.2 Should the base evidence item be an extraction result?

**Matt's proposal (as relayed, 2026-08):** first-order evidence items are *data extraction
result* objects, which relate to a data item, which relates to a document. Every first-level
evidence item is then conceptually an extraction result.

**The case for it.** It puts arrow 1 on every item *by construction* — no span can exist
without a record of how it was obtained. It unifies human and machine curation (a curator
quoting a paper is an extractor with a human agent). And it makes the item/line split carry
exactly the two provenances §3 argues for, rather than leaving arrow-1 provenance optional and
therefore usually absent.

**The case against, which I find stronger.** It inverts generality. The base class should be
what is *always* true; the specialisation carries the optional extra.

1. **It overfits to pipelines** — the §1 constraint. N1's concordance is not an extraction:
   three ontologies independently carry the string `LECD`, and nothing was extracted from
   anything. N2's consortium decision is not an extraction. Forcing these under an
   extraction-result parent is a worse misfit than the `TextSpan` one they already have.
2. **It taxes the simple case** — the §1 gatekeeper constraint. The adoption pitch becomes
   "your quote is a DataExtractionResult". A verbatim sentence is a fact about the document; it
   is true whether or not anyone extracted it.
3. **The middle level is unoccupied.** Wherever the corpus has a span at all, the span and the document are
   adjacent. What the intermediate `DataItem` would hold is unclear — and as relayed, "a data
   item (a paper)" reads as collapsing `DataItem` into `Document`, which the current model keeps
   apart (`TextSpan` *is* the `sepio:DataItem`; `Document` is what it is `reported_in`). **This
   needs clarifying with Matt before it can be evaluated properly** — I may be arguing against a
   position he does not hold.

**The synthesis, and it is already in this spec.** §4.2's A/C shapes get Matt's benefit without
his cost: `TextMiningResult is_a TextSpan`, so extraction provenance is the *same vocabulary at
the same place*, and a C instance with only `value` + `reported_in` validates identically to an
A. Keep A as the base. Then give Matt the thing he actually wants as **guidance plus a profile
constraint, not a superclass**: any *machine-produced* item MUST be emitted as C with its
extraction provenance populated; human- and database-derived items stay A. That makes arrow-1
provenance mandatory exactly where it is meaningful and absent exactly where it would be
fiction.

Naming note: `../requirements.md` calls this `TextMiningAnalysisResult`; §4.2 and mondo-ai call
it `TextMiningResult`. Settle on one before either escapes into a schema.

### 7.3 Where the grounding chain goes — the resolution of R26

The natural follow-on: can SEPIO's own provenance vocabulary carry the whole
snippet → ontology grounding process, per-step quality values included, on each evidence item?
Checked against every class in [`../schema/sepio_classes.yaml`](../schema/sepio_classes.yaml)
and tested on M3's real four-step chain (2026-08-15).

**The mechanism exists.** Three hooks, all reachable from every evidence item:

| Hook | Gives you | Does not give you |
|---|---|---|
| `derived_from: InformationEntity[]` | the lineage chain — each step an entity pointing at its predecessor | multivalued, so a **DAG, not a sequence** |
| `contributions: Contribution[]` | per-step attribution: `contributor: Agent`, `activity_type: Coding`, `date` | unordered bag; no number |
| `Entity.extensions: Extension[]` | the official escape hatch, on every entity | `Extension.value` has no declared range → `default_range: string` |

Plus `specified_by` (the method) and `record_metadata` — neither numeric. A pure `derived_from`
recursion of `DataItem`s expressing the gemifloxacin chain **validates against
`sepio_classes.yaml` unmodified**, so this is a real option, not a straw man.

**Three things are missing, and they are the three MeDIC relies on:**

1. **No numeric slot anywhere in the provenance vocabulary.** Entity, InformationEntity,
   Statement, EvidenceLine, Document, DataItem, StudyResult, DataSet, Activity, Contribution,
   Agent, Coding, Qualifier, Expression, Extension, RecordMetadata, Characteristic, StudyGroup —
   not one float. Per-step confidence comes back as `'0.95'`, a string in an untyped bag. The
   only `value: float` in the stack is sieve's own `Score`, which is an *evidence-strength*
   object — precisely the slot §7.1 forbids arrow-1 numbers from entering. **The one typed home
   available is the one that must not be used.**
2. **No ordering.** `derived_from` is multivalued; the sequence is convention.
3. **No contiguity.** MeDIC's I-8 invariant (`pipeline[n].output_value ==
   pipeline[n+1].input_value`) has no SEPIO expression.

Also: `designates_type` appears in none of the three schemas, so polymorphic inlining under
`derived_from: InformationEntity` validates by validator permissiveness, not by design.

**Measured, same four steps, both validated:**

| | Pure SEPIO `derived_from` | Profile extension on shape C |
|---|---|---|
| Lines | 39 | **7** |
| `confidence` type | `str` | `float` |
| Ordering | implicit — walk the chain | explicit list |
| Contiguity check | not expressible | mechanically checkable |
| Drop the chain → | — | still a valid `TextSpan` |

**This is not a SEPIO deficiency.** It is the same boundary as §7: SEPIO models *attribution and
lineage* — who made this information entity, and from what — and delegates transformation
quality to W3C PROV / DQV. `specified_by`, `derived_from` and `extensions` are the link-out
hooks. Asking SEPIO for per-step grounding confidence is asking it to be a data-quality model.

**Resolution of R26.** One optional ordered slot on shape C, not a bending of the native
provenance slots:

```yaml
grounding:                       # ordered; arrow-1 quality ONLY (§7.1)
  - category: TRANSLATION        # EXTRACTION | TRANSLATION | GROUNDING | NORMALIZATION
    input_value: Гемифлоксацин
    output_value: Gemifloxacin
    confidence: 0.95
    confidence_basis: PRIOR      # MEASURED | DETERMINISTIC | PRIOR | SELF_REPORTED
    performed_by: wikidata:Q116709136
    tool_version: 0.3.6
    flags: [unreviewed_machine]
```

It stays compatible rather than forking: the profile shape maps down onto `derived_from` +
`contributions` + `extensions`, order becoming the chain and numbers becoming strings. Typing is
lost going down — that is the honest cost — but it maps. And `confidence_basis` is the same
`basis` enum the matrix already recommends for R13, so the two land together.

**This also dissolves Q8.** The motivation for making every first-order item an extraction result
is presumably that extraction provenance must always have a home. If shape C carries a typed,
ordered chain *and the profile requires C for machine-produced items*, that guarantee holds
without forcing N1's concordance or N2's consortium decision to pretend they are extractions.

**Caveat on scope.** `sepio_classes.yaml` is a **trimmed** vendored copy (§5). Upstream SEPIO may
carry provenance machinery that was cut here. Confirm against the real model before taking any
of this to Matt.

## 8. Requirements

Derived from the 9-record corpus. Each requirement names the examples that force it; the
traceability matrix is in [`analysis/requirements-matrix.md`](analysis/requirements-matrix.md).
`T1` = must be in the microschema, `T2` = SEPIO Monarch only, `T1?` = contested (§10).

| ID | Requirement | Track | Forced by |
|---|---|---|---|
| **R1** | `direction` carries polarity only: SUPPORTS / REFUTES / NEUTRAL | T1 | D2, D3, M2 |
| **R2** | `strength` is a separate axis from direction; DisMech `PARTIAL` → `SUPPORTS` + `WEAK` | T1 | D1, D2 |
| **R3** | a line-level `evidence_source` axis bound to ECO branches | T1 | D1, D3, M1 |
| **R4** | an evidence item is a verbatim span + the document it is `reported_in` | T1 | all |
| **R5** | a line groups co-directional items sharing direction + strength + source | T1 | D2, M1 |
| **R6** | a statement may carry many lines, including mutually opposing ones | T1 | D2, D3, N1 |
| **R7** | evidence attaches at several granularities: statement, causal edge, hypothesis, discussion | T1 | D1, D3 |
| **R8** | the same document may back several *distinct* lines with different spans | T1 | D2, D3 |
| **R9** | an explicit, inspectable synthesis object (summary + score + method + cited items) | T2 | D2, M1, N1, N3 |
| **R10** | provenance of the *item* — who produced the data | T2 | M3, N2 |
| **R11** | provenance of the *interpretation* — who read the item as evidence, when, under which guideline/model | T2 (**T1?**) | D1, D3, M3, N3 |
| **R12** | declared, revisable **trust level** per interpreting agent, distinct from a model's self-reported confidence | T2 | N2, N3 |
| **R13** | data-quality signals must not be readable as evidence strength | T1+T2 | M1, M2, M3 |
| **R14** | temporality and supersession — later evidence that reverses earlier evidence | *unmet* | D2, ALS/AMX0035 (§8.1) |
| **R15** | defeaters — an argument that an item is *inadmissible* as evidence, not that the claim is false | *unmet* | D3 |
| **R16** | operational/QC values (`NO_EVIDENCE`, `WRONG_STATEMENT`, extraction flags) stay out of the evidence model | T1 | D-schema, M2 |
| **R17** | a statement-level confidence tier (DisMech `ESTABLISHED`/`PROVISIONAL`/`HYPOTHETICAL`) | T1? | D1, D2 |
| **R18** | curation status + a decision history with rationale and certainty | T2 | N1, N3 |
| **R19** | lines groupable under competing hypotheses, including deprecated ones | T2 | D1, D2 |
| **R20** | corroboration must distinguish *independent* sources from republications of one source | T2 | M1, N1 |
| **R21** | an ordered, contiguous transformation chain survives as a unit inside one item | T2 | M1, M3 |
| **R22** | negation / limitation scope: a span that restricts a claim made elsewhere | T1 | M2 |
| **R23** | evidence attaches to a host's own structured statement — association-style `(s,p,o)` or attribute-style — without the kernel restating it | T1 | D1, M1, M2, N1, N2 |
| **R24** | one host class may carry several independently evidenced slots, not just one | T1 | *[anticipated]* |
| **R25** | `statement_text` is a generated human-readable rendering, never a verbatim span | T1 | all nine |
| **R26** | entity-level extraction/grounding chains are ordered, live on the item, and are arrow-1 quality — never evidence strength | T2 | M2, M3, N1 |
| **R27** | a record declares the grouping convention it was produced under, machine-checkably | T1 | Sierra's nine encodings, D2 |
| **R28** | the actionable core is separable from the trace, so a reader can take a view proportionate to its need | T1+T2 | N1, M3 |

**R23, R24 and R25 are met by the kernel today** and were verified against `minimal.yaml` on
2026-08-15 (§3.2). What is missing is guidance, not schema — with one exception, D1's `_host`,
which wants an optional `about` slot. R26 was the open one: §4.2's shape C has
`extraction_method` and `text_location` but no ordered per-entity chain, and the corpus (M2)
shows the failure is in the *composition* of steps, which an unordered bag cannot express.
**§7.3 resolves it** — one optional ordered `grounding` slot on shape C, carrying
`confidence_basis`, kept out of every evidence-strength slot.

### 8.1 The unmet requirements

**R14 (temporality/supersession).** DisMech records the ALS drug AMX0035 with one `SUPPORT`
item from the phase-2 CENTAUR trial and two `REFUTE` items from the phase-3 PHOENIX trial and
the 2024 market withdrawal. A naive tally says 1:2. The truth is that the phase-3 result
*supersedes* the phase-2 result; they are not two votes. Neither profile can say this today,
and any aggregation function that treats them as independent lines is wrong. This is the same
shape as HABP2 (D2), where a 2015 report is superseded by four replication failures.

**R15 (defeaters).** DisMech's `Discussion` on ADSA argues that the `Rnf170`-null mouse
phenotype *cannot be used as evidence* for a loss-of-function mechanism, because the null
genotype models the recessive human disease, not the dominant allele. This is not counter-
evidence about the claim; it is an argument about the *admissibility* of an evidence line — an
undercutting defeater. SEPIO's nesting (an EvidenceLine whose target is another EvidenceLine)
is the natural home, but nothing in either profile currently expresses it and no guidance
exists. **This is the strongest single argument in the corpus for keeping the normalised
representation**, and I would put it in front of Matt first.

**R17** is listed as contested rather than unmet: DisMech has `MechanismConfidenceEnum` today,
and SEPIO `Statement` has `direction`/`strength`/`score` slots that could carry it, but the
microschema drops them and it is unclear whether a statement-level tier should be authored or
derived from the lines.

## 9. Adoption path per resource

| Resource | Today | Next step | Cost |
|---|---|---|---|
| **DisMech** | flat `EvidenceItem` list; `supports` enum conflates 3 concerns; no agent/interpretation provenance despite being AI-curated | adopt Track 1 via the existing `dismech_to_minimal` transform; split `supports`; drop `NO_EVIDENCE`/`WRONG_STATEMENT` from released data | days |
| **MeDIC** | best-in-class provenance, **no** evidence model: no direction, one implicit SUPPORTS | Stage 0 annotate (`class_uri`/`slot_uri`), Stage 1 unify its two evidence-kind vocabularies onto the kernel's two axes, Stage 2 add `direction` + `strength` + `Document` + synthesis | Stage 0 hours, Stage 1 days, Stage 2 1–2 weeks |
| **mondo-ai** | already on SIEVE/SEPIO; camelCase copy of the model | re-point its import at sieve's snake_case kernel; contribute its `TextMiningResult` back into `minimal.yaml` | days |
| **sieve** | owns both schemas | close blockers B1–B4; land phase 3 (C) and phase 4 (evidence-source axis) | weeks |
| **Mondo / Monarch KG** | axiom annotations; Biolink | out of scope here; watch the Biolink `begets` / nearest-source pattern as prior art for optional richer provenance | — |

**Hard constraint for any MeDIC↔sieve integration** (medic §6 stage 4, H1): MeDIC is a
deterministic build system, sieve is a stateful workflow system. *Curation decisions must be
inputs to the MeDIC build, never outputs of it* — a verdict that lives only in sieve's DuckDB
is silently reverted by the next rebuild.

## 10. Open questions and blockers

Inherited from the sieve specs:

- **B1 — kernel home and id.** `https://w3id.org/sepio/minimal` is proposed but unconfirmed.
  It is baked into every downstream import; this should be a SEPIO-project decision, not a
  unilateral sieve one. *Blocks broad adoption.*
- **B2 — real `meaning:` IRIs.** The ECO branch terms for `EvidenceSource` and the
  publication-type IRIs for `DocumentType` must be looked up (OLS), not invented.
- **B3 — mondo-ai divergence.** camelCase / `example.org` copy vs sieve's snake_case + real
  SEPIO URIs. Intended; resolved when mondo-ai re-points its import.
- **B4 — naming.** The microschema has been informally called "the dismech model", which is a
  misnomer and will misdirect adopters. Settle the name before promoting it.

New, from the corpus:

- **Q1 — line granularity guidance.** Matt's original sketch minted one line per snippet; the
  agreed rule is "group by direction + strength + source + document, split only when the
  reasoning differs". D2 shows three distinct arguments from *one* paper, which must be three
  lines under that rule. Extraction pipelines need this written down or they will not converge.
- **Q2 — does item reuse survive contact with reality?** Sierra's objection is empirically
  supported: D1 shows DisMech duplicating PMID:25604431 four times with four different
  snippets, and every pipeline in the corpus mints fresh items. If reuse never happens, the
  item/line split is paying for a capability nobody uses — *except* that the split is also what
  carries interpretation provenance (R11), which is used. Decide which justification we are
  actually relying on.
- **Q3 — how much agent provenance belongs in Track 1?** See §4.3. Options: (a) keep Track 1
  agent-free and accept that AI-curated resources reach into Track 2; (b) add a single optional
  `interpreted_by` slot on `EvidenceLine`; (c) add a minimal `Agent` class. **[inferred]** — the
  notes do not settle this; my instinct is (b), because it costs one slot and unblocks DisMech.
- **Q4 — R14 supersession.** Model as a relation between lines (`supersedes`), as a property of
  the item (study phase / date), or leave to synthesis prose? Needs a SEPIO answer.
- **Q5 — R15 defeaters.** Is an EvidenceLine targeting another EvidenceLine legal in SEPIO, and
  if so what is the pattern? Ask Matt directly.
- **Q6 — independence (R20).** MeDIC's noisy-OR treats two EMA documents about the same active
  substance as two independent corroborations, yielding 0.999998 for a pair whose reliability
  tier is only MEDIUM. Corroboration arithmetic needs a notion of source independence.
- **Q7 — vocabulary contributions upward.** `EvidenceSource: REGULATORY` and `DocumentType:
  REGULATORY_LABEL` are missing and MeDIC is ~9,700 rows of the use case; structured character
  offsets on `TextMiningResult` likewise. Feed these into SEPIO before B2 closes.
- **Q8 — is the base item an extraction result?** §7.2. My position is no: keep `TextSpan` as
  the base, make C mandatory for machine-produced items by profile constraint. §7.3 removes the
  main reason to say yes, by giving extraction provenance a typed, ordered home on C. What
  remains open is narrower: the relayed proposal collapses `DataItem` into `Document` in a way I
  may be misreading — **ask Matt what the intermediate level holds** before arguing the case.
- **Q9 — one `about` slot, or none?** D1 had to invent `_host:` to say which node a claim
  belongs to (§3.2). One optional `about: uriorcurie` on `EvidencedClaim` fixes it at the cost
  of one slot. The alternative is to declare that out-of-host claims are simply out of scope for
  Track 1, which is defensible but leaves the transform outputs with nowhere to put attachment.
- **Q10 — which "quality"?** §7.1. MeDIC's definition is arrow 1, `requirements.md`'s is
  arrow 2. Both are needed and the spec currently names only one. Settle the vocabulary before
  R13 gets implemented as a constraint, or the constraint will police the wrong number.
- **Q11 — can an EvidenceLine have zero items? CLOSED.** §4.5. The premise was wrong: a
  testimony is itself an item, so the standalone expert assertion has one. What replaces it is a
  smaller question, **Q12**.
- **Q12 — does `EvidenceSource` need `EXPERT_TESTIMONY`?** §4.6. `EXPERT_CONSENSUS` is a group
  agreeing; an individual clinician asserting from experience is not that. Either add a value, or
  rule that `EvidenceItemType: TESTIMONY` plus `StatementTraceability` already carries it and the
  source axis stays as it is.
- **Q13 — does the convention get declared, or constrained?** §3.3, R27. Either every record
  carries a `GroupingConvention`, or the profile forbids all but one and CI enforces it. The
  second is stronger and costs producers more. Sierra's recommendation list leans that way
  (`maximum_cardinality: 1`, `designates_type: true`, cap nesting depth in CI).
- **Q14 — is more trace better, worse, or only more expensive?** §3.4. Nobody has measured an
  agent's verdict quality against trace depth, and mondo-ai's 165,818 items are all UNREVIEWED,
  so there is no human baseline either. This is an experiment, not a modelling decision, and it
  should be run before Track 2 is scaled up.


## 11. Non-goals

- Not registering the w3id in this cycle.
- Not migrating existing data anywhere; Track 1 adoption is greenfield plus a transform.
- Not specifying scoring *policy* (weights, thresholds). Those are governance, and per the
  vision they start as organisational defaults and are revised through community deliberation.
- Not building a second curation UI. sieve is it.
- Not solving calibration of AI trust scores. The scores are declared human judgements about
  interpreters, and are explicitly *not* claims about model-internal confidence.

## 12. Glossary

**Statement** — a claim of purported truth made by an agent. **EvidenceLine** — an
evidence-based argument for or against a statement, the output of an interpretation act.
**EvidenceItem** — a *role*: any information entity used in such an argument. **DataItem** — a
class; a discrete piece of acquired information, e.g. a text span. **Contribution** — an action
by an agent toward creating/modifying/validating an information entity. **Profile** — a
constrained, application-specific view of the SEPIO core information model. **NER (Net Evidence
Ratio)** — `(S⁺ − S⁻)/(S⁺ + S⁻ + S⁰)` over evidence lines. **Concordance** — agreement between
independent sources, used as evidence in mondo-ai.

## 13. Related documents

In this repo:

- [`../specs/2026-07-31-minimal-microschema-and-sieve-alignment-design.md`](../specs/2026-07-31-minimal-microschema-and-sieve-alignment-design.md) — kernel architecture, A/C shapes, R1/R2 reconciliations, blockers B1–B4
- [`../docs/monarch-evidence.md`](../docs/monarch-evidence.md) — worked DisMech → minimal → sieve transform
- [`../issues/issue_sepio_minimal_microschema.md`](../issues/issue_sepio_minimal_microschema.md) — the existing SEPIO coordination asks
- [`../issues/issue_kernel_item_range.md`](../issues/issue_kernel_item_range.md) — the corpus finding that changes the kernel's class list
- [`../issues/issue_unmet_evidence_requirements.md`](../issues/issue_unmet_evidence_requirements.md) — R14/R15/R20 as questions for SEPIO
- [`../requirements.md`](../requirements.md) — the working note behind §3.2 and R23–R26; folded
  in on 2026-08-15 and kept as the original statement of the host-shape requirement
- [`../tests/test_monarch_evidence_corpus.py`](../tests/test_monarch_evidence_corpus.py) — keeps
  the corpus validating against the kernel and its `challenges:` ids in sync with §8

Elsewhere:

- `~/ws/notes/evidence/docs/monarch-hackathon-evidence-briefing.md` — the two-track plan, half-pager
- `~/ws/notes/evidence/docs/vision.md` — evidence-first curation, trust accumulation, governance
- `~/ws/notes/evidence/background/{evidence_team_slack,evidence_scratchpad}.md` — the source notes
- `~/ws/projects/medic/docs/sepio-sieve-alignment.md` — the evidence/provenance/quality analysis
- ACMG 2015 variant-interpretation guidelines; ClinGen gene-validity framework — prior art for
  systematic evidence interpretation, and the models SEPIO was validated against
