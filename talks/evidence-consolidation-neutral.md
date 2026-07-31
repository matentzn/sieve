# Evidence Models Across Monarch Repositories

*Factual briefing deck · Nico Matentzoglu · 2026-07-12*

> Neutral reference slides. Content only — no speaker notes. Each slide states facts,
> definitions, or verbatim schema/code. Sources noted where content is drawn from a repo.

---

## Slide 1 — Title

- **Evidence models across Monarch repositories**
- Current state, two consolidation options, migration examples
- 2026-07-12

---

## Slide 2 — Context

- A growing share of assertions entering Monarch knowledge bases is machine-generated
  (extraction, synthesis, drafting) rather than manually authored.
- Examples of AI-assisted pipelines in the ecosystem: DisMech, deep-research artifact
  ingestion.
- This slide states a trend; it does not quantify it.

---

## Slide 3 — Two functions "evidence" serves

Records observed in current schemas serve one of two functions:

| Function | Answers | Typical fields |
|---|---|---|
| **Scientific evidence** | Does a source support/refute this claim? | reference, snippet, direction, ECO code |
| **Provenance / attribution** | Who or what produced this statement, from where? | agent/method, source, knowledge level |

- In manual curation, provenance is often implicit (the curator's identity).
- Machine-generated statements carry no implicit human attribution; the fields above are
  the explicit record.

---

## Slide 4 — Evidence models currently in use (observed)

At least three distinct evidence models are in active use. Others likely exist across
Monarch repos; an exhaustive count has not been made.

| Repository | Evidence representation |
|---|---|
| **DisMech** | flat `EvidenceItem` class |
| **Sieve** | polymorphic `Evidence` hierarchy |
| **koza ingests** (e.g. alliance-genotype-ingest) | Biolink association provenance slots |

- The three are not interoperable: the same concept is spelled differently in each.

---

## Slide 5 — Model 1: DisMech `EvidenceItem`

*Source: `monarch-initiative/dismech`, `src/dismech/schema/dismech.yaml`*

```yaml
EvidenceItem:
  slots: [reference, reference_title, supports, evidence_source, snippet, explanation, images]

EvidenceItemSupportEnum:   [SUPPORT, REFUTE, PARTIAL, NO_EVIDENCE, WRONG_STATEMENT]
EvidenceSourceEnum:        [HUMAN_CLINICAL, MODEL_ORGANISM, IN_VITRO, COMPUTATIONAL, OTHER]
```

- `reference` uses `implements: linkml:authoritative_reference`; `snippet` uses `linkml:excerpt`.
- `evidence` is a `multivalued`, `inlined_as_list` slot reused on ~8 classes.
- Validated at runtime with `linkml.validator.Validator`.

---

## Slide 6 — Model 2: Sieve `Evidence` hierarchy

*Source: `sieve`, `schema/curation_model.yaml`*

```yaml
Evidence (abstract):
  slots: [evidence_type, direction, evidence_strength, rating, eco_code, eco_label, description]

# subclasses (designates_type on evidence_type):
ConcordanceEvidence | LiteratureEvidence | ExpertReviewEvidence | ComputationalEvidence

EvidenceDirection: [SUPPORTS, CONTRADICTS, UNCERTAIN]
EvidenceType:      [CONCORDANCE, LITERATURE, EXPERT_REVIEW, COMPUTATIONAL, OTHER]
```

- Adds `evidence_strength` (float 0–1) and a separate `EvidenceSynthesis` class
  (summary + confidence).

---

## Slide 7 — Model 3: koza / alliance-genotype-ingest

*Source: `monarch-initiative/alliance-genotype-ingest`, `src/alliance_genotype/allele.py`*

Each `VariantToGeneAssociation` (Biolink) is stamped with:

```python
primary_knowledge_source    = "infores:agrkb"                                  # or MGI/RGD/ZFIN
aggregator_knowledge_source = ["infores:monarchinitiative", "infores:agrkb"]
knowledge_level             = KnowledgeLevelEnum.knowledge_assertion
agent_type                  = AgentTypeEnum.manual_agent
```

- `publications` and `has_evidence` are **not** set in this ingest.
- `agent_type` and `knowledge_level` are Biolink enums (values include
  `automated_agent`, `text_mining_agent`, `computational_model`, `prediction`, etc.).

---

## Slide 8 — Consolidation: two options

| | **Option A — SEPIO-aligned** | **Option B — Shared flat microschema** |
|---|---|---|
| Form | Provenance graph (assertion → evidence line → item → source) | One `EvidenceItem` class, imported |
| Expressivity | High | Limited |
| Authoring complexity | High | Low |
| Provenance graph / evidence-for-evidence | Yes | No |
| Existing adopters | GO-CAM, ClinGen | (proposed; DisMech PoC) |
| Relationship | — | Can be defined as a strict subset of A |

- Both options address the same fact: one evidence model instead of many.

---

## Slide 9 — Option A: SEPIO (facts)

- **SEPIO** = Scientific Evidence and Provenance Information Ontology.
- Core pattern: an *assertion* is supported by *evidence lines*, composed of *evidence
  items*, which reference *sources*.
- First-class *agents*, *activities*, *methods*, *dates*; supports evidence about
  evidence, and disputing evidence.
- In use by GO-CAM and ClinGen (variant pathogenicity).
- Structure is a graph, not a flat record.

---

## Slide 10 — Option B: shared microschema (facts)

- A single LinkML module (`evidence.yaml`) published at a stable URI, imported by other
  schemas.
- One flat `EvidenceItem` covering both functions from Slide 3:
  - Scientific: `reference`, `snippet`, `direction`, `strength`, `eco_code`
  - Provenance: `agent_type`, `knowledge_level`, `knowledge_source`
- Consuming schemas `imports:` it and point their `evidence` slot at the shared class.
- Does not model a provenance graph or evidence-for-evidence.

---

## Slide 11 — Migration [1/3]: mechanism

- Author `evidence.yaml` once → publish at `w3id.org/linkml/microschemas/evidence`.
- Each consuming schema adds `imports: [evidence]` and references the shared class.
- LinkML supports import by URL; precedent: `linkml-microschemas-envar` imports a shared
  profile from a raw GitHub URL.
- One class, two field groups (scientific / provenance) per Slide 9.

---

## Slide 12 — Migration [2/3]: DisMech

*Before — DisMech defines its own:*
```yaml
EvidenceItem: {slots: [reference, reference_title, supports, evidence_source, snippet, explanation, images]}
EvidenceItemSupportEnum: [SUPPORT, REFUTE, PARTIAL, NO_EVIDENCE, WRONG_STATEMENT]
```
*After — DisMech imports the shared model:*
```yaml
imports: [linkml:types, evidence]
slots:
  evidence: {range: EvidenceItem, multivalued: true, inlined_as_list: true}
```
- Data change: rename `supports → direction`, values `SUPPORT → SUPPORTS`, `REFUTE → REFUTES`.
- The 8 consuming classes are unchanged (they reference the `evidence` slot).
- PoC acceptance: import resolves; `gen-python` runs; one real record converts + validates;
  old enum value fails validation.

---

## Slide 13 — Migration [3/3]: koza / alliance-genotype-ingest

*Today — per-ingest, spelled in Biolink:*
```python
primary_knowledge_source, aggregator_knowledge_source,
knowledge_level = knowledge_assertion,
agent_type      = manual_agent
```
*Consolidated — same slots defined once as the provenance profile of the shared model:*
- `knowledge_level`, `agent_type`, `knowledge_source` defined in `evidence.yaml`, mapped
  to the corresponding Biolink association slots.
- Ingests continue emitting Biolink edges; the evidence vocabulary is defined once.
- `agent_type` value range already includes `automated_agent`, `text_mining_agent`,
  `computational_model`.

---

## Slide 14 — Open design question: level of evidence

*Source: `monarch-initiative/dismech` issue #5000*

- Proposal: add an optional `evidence_level` slot (study strength) — e.g. GRADE
  (`HIGH/MODERATE/LOW/VERY_LOW`) or Oxford CEBM levels.
- Axis is **orthogonal** to `evidence_source` (study *type*): an RCT and a case series are
  both `HUMAN_CLINICAL`.
- Distinct from Sieve's `evidence_strength` (a continuous 0–1 float, not bound to a scheme).
- Pilot (issue #5000, PR #5090) findings, verbatim scope:
  - 0.47% of pathophysiology evidence items cite a MEDLINE-tagged RCT; SR+RCT+guideline = 2.26%.
  - CEBM fits intervention sections better (66.7% of `clinical_trials` are SR/RCT/guideline-tier).
  - Source quality and per-claim interpretation are separable axes (celiac ZED1227 example).
  - GRADE inter-annotator agreement among trained methodologists: κ≈0.44 (Hartling 2012).
- Status: framework (GRADE vs CEBM vs custom) not decided.

---

## Slide 15 — Summary of facts

- Multiple non-interoperable evidence models are in use; three confirmed
  (DisMech, Sieve, koza ingests).
- Two established directions exist: SEPIO-aligned (graph) and a shared flat microschema
  (import).
- A shared microschema can be defined as a strict subset of SEPIO.
- Migration mechanism (LinkML import by URL) is proven; a DisMech PoC scopes the change.
- Level-of-evidence (`evidence_level`) is an open, orthogonal design question (dismech #5000).

---

### Appendix (reference)

- **A1 — Field mapping, flat model → SEPIO:** `reference` → evidence item source;
  `agent_type` → SEPIO agent; `knowledge_level` / `evidence_level` → assertion method /
  criterion; `direction` → evidence-line polarity.
- **A2 — Biolink association provenance slots:** `primary_knowledge_source`,
  `aggregator_knowledge_source`, `knowledge_level`, `agent_type`, `publications`,
  `has_evidence`.
- **A3 — Source files:** dismech `src/dismech/schema/dismech.yaml`; sieve
  `schema/curation_model.yaml`; alliance-genotype `src/alliance_genotype/allele.py`;
  envar `src/linkml_microschemas_envar/schema/`.
