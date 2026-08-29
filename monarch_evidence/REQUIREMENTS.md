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
- **B6. Declare the interpretation scope** — how much of the document was read before the line
  was drawn (snippet, sentence, paragraph, abstract, full paper), and which text it was read
  from (*proposed, `issues/issue_interpretation_scope.md`*).

## C. Evaluating evidence for and against

- **C1. Direction carries polarity only**: SUPPORTS / REFUTES / NEUTRAL (R1).
- **C2. Strength is a separate axis** from direction (R2), alongside a source axis bound to ECO
  branches (R3).
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
  (R20, **unmet**).
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

Each row is independently fixable and lands a requirement above. Ordered cheapest-first; 1–4 are
schema splits that need no new curation, 5–8 add a slot, 9–12 need a decision before code.
Counts are from the linked issues (130,693 evidence items across `kb/`).

| # | Defect today | Fix | Issues | Req |
|---|---|---|---|---|
| 1 | **`supports` conflates direction, strength and QC** in one enum — SUPPORT 91.1%, PARTIAL 8.1%, REFUTE 0.4%, plus two QC values | split into `direction` (SUPPORTS/REFUTES/NEUTRAL) and `strength`; `PARTIAL` → SUPPORTS + WEAK | #5000, #7439 | C1, C2 |
| 2 | **QC verdicts sit in the evidence slot** — `NO_EVIDENCE` (448) and `WRONG_STATEMENT` (1) say the curation failed, not what the source shows | move to a QC slot, drop from released data | *none direct*; cf. #4525 | E5 |
| 3 | **No strength axis at all** — an n=1 case report and a 138,000-person Mendelian randomization are both `HUMAN_CLINICAL` + `SUPPORT` | study design + sample size, or a level tier (GRADE / Oxford CEBM) | #9421, #9833, #9827, #9785, #9710 | C2, D1 |
| 4 | **`evidence_source` conflates the system studied with the document kind** — `OTHER` is 16.1% and doubles as "review article" | split out `document_type`; decide the GeneReviews and mixed-source conventions | #7439, #3635, #6997 | C2, F2 |
| 5 | **No source standing** — `ReferenceTagEnum` has exactly one permitted value, so a *retired* GeneReviews chapter reads as current | a standing axis: retracted / retired / superseded / preprint | #9840 | C6 |
| 6 | **Snippet text-source unrecorded** — a quote from PDF-extracted text (ligatures, broken words) is indistinguishable from a clean abstract quote; DOI snippets (5,047, 6.7%) skip validation entirely | record which cached text the snippet came from; unskip DOI in the validator | #9711, #7514 | B1, B5 |
| 7 | **Interpretation scope unrecorded** — nothing says how much of the paper was read before the line was drawn | scope slot on the evidence line | #9711 | B6 |
| 8 | **Interpretation provenance exists but does not reach the evidence** — `history/` holds 4,568 disorder session records, 4,207 with an `ai_agent` actor naming model and tool, plus the reasoning in prose; but its finest grain is `sections:` (phenotypes, treatments…), `EvidenceItem` still has its seven original slots, and no session id appears anywhere in `kb/` | carry the session id down to the line or item, so a snippet resolves to the reading that produced it | *none open* | E1, E2 |
| 9 | **Two snippets from one paper: one argument or two?** — sibling items with no grouping | evidence lines, plus a declared grouping convention | #7439 | C4, C11 |
| 10 | **Contested claims are unresolved and unrendered** — 11 nodes carry both SUPPORT and REFUTE; the renderer shows a flat list and no verdict | a synthesis object over the lines, and rendering for it | #4694 | C3, D2 |
| 11 | **Single-source claims read as corroborated** — gene–disease links resting on Orphanet alone | corroboration expectation; distinguish independent sources from republications | #5035 | C8 |
| 12 | **Frequency bands float free** — 715 ambiguous bands with no machine-readable link to the item that grounds them | attach evidence at the band, not just the phenotype | #9390 | A4, A5 |

Smaller and already specified: publication year exposed to renderers without being read as an
observation date (#7517, → C6). Still a scope question rather than a defect: where purely
computational evidence belongs (#9794, → F1).

**#7439 (open) proposes the pilot that carries 1, 4 and 9** — an additive `EvidenceLine` / `DataItem` /
`Document` layer beside native `evidence:`, with `direction_of_evidence_provided` split from
`strength_of_evidence_provided`, `DocumentTypeEnum`, and evidence items grouped under a line.
PR #7445 (merged) already exports the native model to SEPIO statements in KGX, so the mapping
exists in code; what it cannot invent is the information rows 1–8 say is missing.
