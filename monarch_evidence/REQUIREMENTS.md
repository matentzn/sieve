# Requirements for the perfect evidence system

Capability-level requirements, collected from the analyses in this folder. The detailed,
corpus-traced version lives in [`SPEC.md` §8](SPEC.md) (R1–R26) and
[`analysis/requirements-matrix.md`](analysis/requirements-matrix.md); the `(R…)` / `(§…)` tags
below point there. Items marked **unmet** are not expressible in either profile today.

## A. Shape — how evidence attaches to things

- **A1. Embeddable.** A microschema with no dependencies that any resource can import into a
  larger model (§4).
- **A2. The statement lives outside the evidence model**, in the host, and is usually already
  structured — either association style (the statement *is* a triple) or attribute style (the
  predicate is a slot on a record about the subject):

  ```yaml
  # association style                # attribute style
  indication:                        drug:
      drug: X:A                          id: X:A
      disease: Y:B                       indication: Y:B
      relationship: INDICATED            evidence_indication: [...]
      evidence: [...]
  ```

- **A3. One evidence model for both styles** — the kernel must not restate the statement (R23).
- **A4. Several independently evidenced slots** on one host class, not just one (R24).
- **A5. Several attachment granularities**: a statement, a causal edge, a hypothesis group, a
  discussion (R7).
- **A6. The statement is almost never explicit in the source.** What is explicit is the grounded
  triple; any human-readable `statement_text` is a *generated rendering*, never a verbatim
  span (R25).
- **A7. No overfitting.** No class may be shaped around one pipeline's output; a slot proposed by
  one resource is checked against the rest of the corpus first (§1).

## B. Statement alignment — mapping a snippet to a structured question

- **B1. Align a text snippet to the structured statement it bears on**, and keep the verbatim
  span plus the document it was reported in (R4).
- **B2. Alignment is an act, not a property of the snippet.** The same span can support one claim
  and refute another, so direction and strength live on the evidence line, never on the item
  (R1, §7.1).
- **B3. The grounding chain is ordered and survives as a unit**: extraction → translation →
  grounding → normalisation, from surface text to ontology ids, each step with its own
  confidence and basis (R21, R26).

  ```yaml
  snippet: "Aspirin is indicated for hypertension"
  grounding:
    - {category: EXTRACTION,    output_value: "Aspirin",       confidence_basis: MEASURED}
    - {category: GROUNDING,     output_value: DRUGBANK:1234,   confidence: 0.9}
    - {category: NORMALIZATION, output_value: CHEBI:15365,     confidence: 0.9}
  ```

- **B4. Partial alignment must be expressible** — a span that narrows, qualifies or explicitly
  restricts a claim made elsewhere ("not indicated for …") (R22).
- **B5. Three different numbers, never merged**: grounding fidelity (did we get the right ids?),
  interpretation correctness (did we read this as bearing on the claim correctly?), and evidence
  strength (how much does it move the claim?) (§7.1).
- **B5b. Record the quoted sentence's standing in its source** — did the cited document make the
  observation, relay it with a citation, or relay it with none? This is *citation distance*, and
  it is orthogonal to both study design and inference distance: a strong cohort study relayed
  secondhand and a weak case report described firsthand sit at opposite corners. **We already have
  this slot** — `StatementTraceability` in SPEC §4.6, whose three ECO terms were confirmed against
  OLS — it just lacks a firsthand value and is currently scoped to testimony (#10212, #9951).
  Measured stakes: published quotation-error rates run **14.5–20%**, two thirds of them major.
- **B5d. Record which zone of the citing paper's argument the sentence sits in** — its own result,
  its background, or its synthesis of others' work. Distinct from B5b: that is the epistemic claim
  (firsthand or relayed), this is the structural fact that evidences it. **Derivable, not
  authored** — NLM structured-abstract labels cover 28.5% of the PMID cache and the exact-substring
  guarantee turns a snippet into a byte offset, so the zone is computed, not judged. Maps to CiTO
  (`cito:obtainsBackgroundFrom` vs `cito:citesAsEvidence`); SciCite is the taxonomy to reuse if it
  is ever automated (#10262).
- **B5c. Record what population or entity the evidence was measured in**, not only how much of it
  there was — a cohort of 500 for a broader entity does not evidence a claim about a narrower one
  (#9785, PBD4A).
- **B6. Declare the interpretation scope** — how much of the document was read before the line
  was drawn (snippet, sentence, paragraph, abstract, full paper), and which text it was read
  from (*proposed, `issues/issue_interpretation_scope.md`*).

## C. Evaluating evidence for and against

- **C1. Direction carries polarity only**: SUPPORTS / REFUTES / NEUTRAL (R1). *NEUTRAL is not
  "irrelevant"* — evidence that bears on the claim without favouring either side is a different
  assertion from evidence that does not bear on it at all, and an exporter that equates them
  changes the claim (DisMech #10003).
- **C2. Strength is a separate axis** from direction (R2), alongside a source axis bound to ECO
  branches (R3). **Contested**: DisMech's position is that strength should be *derived* from study
  design, size and replication rather than authored on the item, because a curator can point at
  nothing when challenged on it (design decisions §12, #10003).
- **C2b. Directness is a third axis** — how directly the quoted text asserts the claim, versus
  asserting something the claim follows from. It is judgeable from the snippet and the claim
  alone, which is why DisMech curates it where it will not curate strength (`DirectnessEnum`).
- **C3. Contested claims are first class** — one statement may carry many lines, including
  mutually opposing ones (R6).
- **C4. Line granularity is a rule, not a habit**: group co-directional items sharing direction,
  strength, source and document; split only when the reasoning differs (R5, Q1).
- **C5. One document may back several distinct lines** with different spans (R8).
- **C6. Supersession** — later evidence that reverses earlier evidence is not just another vote
  (R14, **unmet**).
- **C7. Undercutting defeaters** — "that evidence is inadmissible for this claim" is categorically
  different from "that evidence refutes this claim" (R15, **unmet**).
- **C8. Source independence** — two republications of one authority are not two corroborations
  (R20, **unmet**). **Direction is not preserved by citation**: of 613 articles citing three
  myth-*debunking* papers, 468 affirmed the myth (Letrud & Hernes 2019). Counting citations is
  therefore not counting evidence, in sign as well as in weight — see also Greenberg's citation
  distortion taxonomy (bias / amplification / invention) in SPEC §3.4.
- **C9. Absence of evidence** — a source checked with nothing found must be recordable, or there
  is no denominator (§4.4 kind 18, **unmet**).
- **C10. Competing hypotheses** — lines groupable under alternative, possibly deprecated,
  hypotheses (R19).
- **C11. A record declares the grouping convention it was produced under**, machine-checkably —
  otherwise C4 is unenforceable across pipelines (R27).

## D. Evidence strength scoring

- **D1. Every score declares its basis**: MEASURED / DETERMINISTIC / PRIOR / SELF_REPORTED (R13).
- **D2. Aggregation is an inspectable object** — summary, score, method and cited items — not a
  number produced by a hidden script (R9).
- **D3. The aggregate must be able to vary.** A system that returns 1.0 for every record is not
  scoring anything (all 160,187 mondo-ai packets do).
- **D4. Quality numbers may never be written into strength slots.** Chain confidence is a *gate*
  on the line, never the line's score (R13, §7).
- **D5. Optional statement-level tier** (ESTABLISHED / PROVISIONAL / HYPOTHETICAL) — authored or
  derived from the lines is undecided (R17).
- **D6. Scoring policy stays out of the schema.** Weights and thresholds are governance.

## E. Agents, provenance and trust

- **E1. Two provenances**: who produced the item, and who interpreted it as evidence, when, under
  which guideline or model version (R10, R11).
- **E2. Declared, dated, revisable trust per agent** — an organisational judgement about the
  interpreter, distinct from a model's self-reported confidence (R12).
- **E3. Testimony is first-order evidence.** An expert assertion with no retrievable basis is
  itself an item; its traceability is declared (TRACEABLE / CLINICAL_STUDY_REFERENCED /
  UNTRACEABLE). If it cites evidence it is a synthesis, if it does not it is testimony (§4.5).
- **E4. Curation status plus a decision history** with rationale and certainty (R18).
- **E5. Operational and QC values** (`NO_EVIDENCE`, `WRONG_STATEMENT`, extraction flags) stay out
  of the evidence model (R16).

## F. Coverage and interoperability

- **F1. Cover every kind of evidence, not just spans.** Only 4 of the 20 surveyed kinds have a
  span; concordance, measurement, computation, attestation and testimony must not have to invent
  a quote (§4.4, §4.5).
- **F2. Shared enums with real ontology meanings**, looked up in ECO rather than invented
  (§4.6, B2).
- **F3. Lift without re-modelling** — an explicit, tested transform between the minimal profile
  and the richer one (§6).
- **F4. Simple enough to be adopted.** Every slot in the microschema earns its place; the nesting
  must be invisible to a Track 1 adopter (§1).
- **F5. The actionable core is separable from the trace**, so a reader can take a view
  proportionate to their need — a clinician and a debugging developer want different depths
  (R28).

## DisMech — the defects to fix, in order

**State of play (2026-08-29).** PR #10003 shipped and closed #7439. `supports` is now direction
only — SUPPORT / REFUTE / NO_EVIDENCE — with `PARTIAL` and `WRONG_STATEMENT` retired and a new
optional `directness` axis (DIRECT / INDIRECT / UNKNOWN) beside it. Self-contradictory `supports`
gradings fell from 8,285 to 353, a 96% drop. Rows 1 and 2 below are therefore **done**, though not
the way this list framed them: the split landed as direction + *directness*, not direction +
strength, and row 3 is now actively contested rather than merely unbuilt. The SEPIO
`EvidenceLine` / `DataItem` / `Document` nesting was **declined** with reasons (row 9). SEPIO
alignment is carried by `exact_mappings` on the native slots, export-layer only.

Each remaining row is independently fixable and lands a requirement above. Counts are from the
linked issues (147,550 evidence items across `kb/` as of 2026-08-31; `directness` is set on 213).

| # | Defect today | Fix | Issues | Req |
|---|---|---|---|---|
| 1 | ✅ **done** — `supports` was one enum answering several questions; 11,620 `PARTIAL` items carried four different meanings, none of them strength | narrowed to direction only; `PARTIAL` → SUPPORT with `directness` left **unset**, or split into a SUPPORT/REFUTE pair, or NO_EVIDENCE | #7439 → PR #10003 | C1, C2b |
| 2 | ⚠️ **half done** — `WRONG_STATEMENT` retired (its single use became a `history/` record, which is where curation provenance belongs); `NO_EVIDENCE` **kept**, and correctly so — "this source does not bear on the claim" is a real evidential statement, not a QC flag | none; the remaining QC-in-evidence problem is mis-set `supports`, now 353 cases | PR #10003 | E5, C1 |
| 3 | **No strength axis, and disagreement about whether to author one** — an n=1 case report, a narrative review and a 502-patient RCT are identical in every queryable field; the counter-position is that strength must be *derived*, not curated | derive `study_design` from the MeSH `publication_types` already in `references_cache/`; `replication` and publication year are the cheap curated axes; the loss is that nothing can **promote** the strongest item, not just discount weak ones | #9421 (main), #9951, #9833, #9827, #9785, #9710, #5000 | C2, D1 |
| 4 | **`evidence_source` conflates the system studied with the document kind** — `OTHER` is 16.1% and doubles as "review article" | split out `document_type`; decide the GeneReviews and mixed-source conventions | #7439, #3635, #6997 | C2, F2 |
| 5 | **No source standing** — `ReferenceTagEnum` has exactly one permitted value, so a *retired* GeneReviews chapter reads as current | a standing axis: retracted / retired / superseded / preprint | #9840 | C6 |
| 6 | **Snippet text-source unrecorded** — a quote from PDF-extracted text (ligatures, broken words) is indistinguishable from a clean abstract quote; DOI snippets (5,047, 6.7%) skip validation entirely | record which cached text the snippet came from; unskip DOI in the validator | #9711, #7514 | B1, B5 |
| 7 | **Interpretation scope unrecorded** — nothing says how much of the paper was read before the line was drawn | scope slot on the evidence line | #9711 | B6 |
| 8 | **Interpretation provenance exists but does not reach the evidence** — `history/` holds 4,568 disorder session records, 4,207 with an `ai_agent` actor naming model and tool, plus the reasoning in prose; but its finest grain is `sections:` (phenotypes, treatments…), `EvidenceItem` still has its seven original slots, and no session id appears anywhere in `kb/` | carry the session id down to the line or item, so a snippet resolves to the reading that produced it | *none open* | E1, E2 |
| 9 | ❌ **declined, with reasons** — an `EvidenceItem` is held to be already an evidence line over one item and one document, and `ELLIPSIS_INSERTION` lets a single `snippet` carry a discontinuous multi-span quote, which was most of what nesting bought | none for now; revisit only if row 10 forces it | PR #10003 | C4, C11 |
| 10 | **Evidence about other evidence is unrepresentable** — named as the accepted cost of row 9. `glymphatic_dysfunction.yaml` holds a REFUTE (an independent lab found no AQP4 effect) *and* a rebuttal attributing that negative to anaesthetic regimen and tracer route; the flat list records both as parallel primary observations. This is an undercutting defeater in DisMech's own data | a line that targets another line; then a synthesis over them | PR #10003, #4694 | C3, C7, D2 |
| 11 | **Two papers from one lab look like two groups** — an `ESTABLISHED` grade rested on "independent confirmation from a different group" that was the same VU Amsterdam programme, quoting its own introduction citing its own prior work. Also gene–disease links resting on Orphanet alone | a derived check first: `references_cache/` already carries `authors:`, so shared last authors on one node can be flagged without a schema change | #10029, #5035 | C8 |
| 12 | **Frequency bands float free** — 715 ambiguous bands with no link to the item that grounds them. Three failure modes now recorded: a band from a quote stating no frequency; a band from a quote stating a frequency *for a different noun*; and one paper supplying three bands in three sentences with nothing saying which is which. Every gate passed all three | let the band point at its evidence item — validation cannot fix this, since a checker requiring a numeral in the snippet passes the wrong-noun case | #9390, #9785 | A4, A5 |

| 13 | **`supports` cannot say what the evidence is directional *about*** — evidence that refutes a *rival* explanation strengthens the node by elimination, but has to be written as REFUTE, which 572 other uses read as contradicting the node itself | a target for the line, distinct from the node it hangs on | #9421 (comment) | A5, C7 |
| 14 | **No "contested" state for a hypothesis** — `MechanisticHypothesisStatus` offers CANONICAL / ALTERNATIVE / EMERGING / DEPRECATED; a live GOF-vs-haploinsufficiency disagreement had to be filed as DEPRECATED, which means *refuted-and-discardable* rather than *superseded-but-historically-real* | a contested value, and a superseded-vs-refuted distinction | #9785 | C3, C6 |
| 17 | **Nothing says which zone of a paper a snippet came from** — a chick-embryo study cited eight times, twice from its *introduction* stating the human clinical picture. Neither `HUMAN_CLINICAL` nor `MODEL_ORGANISM` is a lie about the quoted sentence and both mislead about the paper: the axis is missing, not mis-set | report-only detector first, at two tiers — deterministic section offsets (28.5% of the cache) and a MeSH proxy — then a `quote_role` enum mapped to CiTO. Proposed independently three times under three names | #10262, #9827, #9951 | B5d |
| 18 | **An invented author attribution survives every gate** — a Perplexity report credited "De Vitis et al." with a figure that belongs to Baccelli et al.; the number was right, the paper does not exist. Snippet validation confirms a quote exists in a *cited* source; nothing checks the attribution in the surrounding prose | a preflight over deep-research reports: `authors:` is present in 99.7% of PMID cache files, so every "X et al." can be asserted against some cited reference. Upstream of curation, not a KB gate | #10262, cf. #4525 | B5b, E5 |
| 16 | **An item cannot say whether the cited paper made the observation or is relaying it** — a review's introduction and a review's own results are both SUPPORT + HUMAN_CLINICAL and both verify against the cache. Curators are reaching for `directness: INDIRECT`, which the schema defines as inference distance, then explaining in prose that they did not mean it | adopt `StatementTraceability` (§4.6) rather than mint a new enum: `ECO:0000033` traceable / `ECO:0006016` clinical-study-referenced / `ECO:0000034` untraceable, plus a firsthand value; `primary_reference` only where the chain is traceable | #10212, #9951 | B5b, E3 |
| 15 | **History-record prose is unverified** — `just validate-history` checks a record's shape, never its `details` against the entry it describes, so a false claim about what was curated is permanent, schema-valid and CI-passing | check assertions about an artifact against the artifact — the same hole `check-source-defect-claims` closed for caches | #9421 (comment) | E1, E4 |

Smaller and already specified: publication year exposed to renderers without being read as an
observation date (#7517, → C6). Still a scope question rather than a defect: where purely
computational evidence belongs (#9794, → F1).

**What the merge settles, and what it does not.** #7439 closed as a *partial* adoption: the axis
split landed, the class nesting did not. The reasoning is worth carrying upward rather than
arguing with — the axes a curator can defend from the snippet and the claim (direction,
directness) were adopted; the axis that needs facts the item does not hold (strength) was
refused. That is a sharper version of our own D1: **the basis of a score decides whether it can
be authored at all.** The two costs are named honestly in the PR — no evidence about evidence
(row 10), and 11,620 items migrated with `directness` deliberately absent, because defaulting
them would have manufactured appraisals no curator made. Absent-means-unassessed is a modelling
choice we should copy.

One empirical finding for SPEC Q2 (does item reuse survive contact with reality?): DisMech
entries that define an evidence list once with a YAML anchor and reuse it by alias **cannot carry
a claim-relative `directness`** on the shared object. Reuse and claim-relative annotation are in
direct tension — which is §7.1's "evidence is a property of the line, never the item", arriving
from the data rather than from theory.
