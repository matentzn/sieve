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
