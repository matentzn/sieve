# Requirements × corpus traceability matrix

Which example forces which requirement, and whether the requirement is met today. Requirement
definitions are in [`../SPEC.md` §8](../SPEC.md#8-requirements).

Legend: **✓** forced/exercised · **T1** in the microschema today · **T2** in the SIEVE profile
today · **✗** not representable in either.

| | D1 | D2 | D3 | M1 | M2 | M3 | N1 | N2 | N3 | Status |
|---|---|---|---|---|---|---|---|---|---|---|
| **R1** direction = polarity only | | ✓ | ✓ | | ✓ | | | | ✓ | T1 |
| **R2** strength separate from direction | ✓ | ✓ | | | | | | | | T1 |
| **R3** line-level evidence_source (ECO) | ✓ | | ✓ | ✓ | | | | | | T1 (IRIs pending, B2) |
| **R4** item = verbatim span + document | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | T1 |
| **R5** line groups co-directional items | | ✓ | | ✓ | | | ✓ | | | T1 (guidance missing, Q1) |
| **R6** many lines, opposing allowed | | ✓ | ✓ | | ✓ | | ✓ | | | T1 |
| **R7** multi-granularity attachment | ✓ | | ✓ | | | | | | | T1 (`HasEvidenceLines` mixin) |
| **R8** one document → several lines | ✓ | ✓ | | | ✓ | | | | | T1 |
| **R9** explicit synthesis object | | ✓ | | ✓ | | | ✓ | | ✓ | T2 |
| **R10** provenance of the item | | | | | | ✓ | | ✓ | | T2 |
| **R11** provenance of the interpretation | ✓ | ✓ | ✓ | ✓ | | ✓ | | ✓ | ✓ | T2 only — **Q3** |
| **R12** declared agent trust level | | | | | | | ✓ | ✓ | ✓ | T2 partial (enum only, no numeric/dated declaration) |
| **R13** data quality ≠ evidence strength | | | | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | **convention only, unenforced** |
| **R14** temporality / supersession | | ✓ | | | | | | | | **✗** |
| **R15** defeaters / admissibility | | | ✓ | | | | | | | **✗** |
| **R16** QC signals out of the model | | ✓ | | | ✓ | ✓ | | | | T1 (by omission) |
| **R17** statement-level confidence tier | ✓ | ✓ | | | | | | | | T2 (`Statement.strength`), dropped in T1 |
| **R18** curation status + decisions | | ✓ | ✓ | | ✓ | | ✓ | ✓ | ✓ | T2 (**never exercised at scale**) |
| **R19** competing hypothesis grouping | ✓ | ✓ | | | | | | | | **✗** |
| **R20** source independence | | | | ✓ | | | ✓ | | | **✗** |
| **R21** ordered transformation chain | | | | ✓ | | ✓ | | | | **✗ in SEPIO** (MeDIC-native) |
| **R22** negation / limitation scope | | | | | ✓ | | | | | T1 (as separate statements) |
| **R23** attaches to host's structured statement | ✓ | | | ✓ | ✓ | | ✓ | ✓ | | T1 (met, guidance missing) |
| **R24** several evidenced slots per host | | | | | | | | | | T1 (met, unexercised) |
| **R25** `statement_text` is generated, not a span | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | T1 (convention only) |
| **R26** ordered entity-level extraction chain | | | | | ✓ | ✓ | ✓ | | | ✗ today — resolution proposed, SPEC §7.3 |

## Two conventions, stated

The `challenges:` list inside each example YAML and the ✓ marks in this table do **not** mean the
same thing, and eight requirements disagree between them as a result. `challenges:` names the
*headline* requirements an example was built to exercise; the matrix marks every requirement the
example *touches*. R4 is the clearest case — the matrix marks all nine, because every example has
a span attached to an identified document, while only M2 declares it. Every disagreement runs in
that direction; no example claims a requirement the matrix denies.

## Verification (2026-08-15)

The `minimal:` blocks are executable, and were run: all nine files parse, and **9 of the 14
`EvidencedClaim` blocks validate against `../../schema/minimal.yaml` with no issues**. The five
failures are M1 and M2×3 and M3, and every one of them fails on exactly two values —
`EvidenceSource: REGULATORY` and `DocumentType: REGULATORY_LABEL` — which the corpus already
marks `PROPOSED` and the SPEC already tracks as Q7. Nothing else in the corpus is broken.

That is worth keeping true. There is no test that enforces it, so the next edit to `minimal.yaml`
can silently invalidate the corpus.

## Reading the matrix

**Six rows are the real work.** R13, R14, R15, R19, R20, R21 are either unrepresentable or
enforced only by convention, and every one of them is needed to compute an aggregate that is not
misleading:

- **R13** is a convention, not a constraint. Nothing in either schema stops someone writing
  MeDIC's `0.855` into `score_of_evidence_provided`. A `confidence_basis`-style enum (M3) would
  turn the convention into a checkable property at essentially zero cost, and would
  simultaneously expose N3's self-reported model confidence for what it is.
- **R14 / R15 / R20** are the three ways a naive tally goes wrong: counting superseded evidence,
  counting an admissibility argument as counter-evidence, and counting republications as
  independent corroboration. D2, D3 and M1/N1 respectively. These are SEPIO questions, not local
  ones.
- **R19** (hypothesis grouping) is DisMech-specific enough that Track 1 should probably not try.
- **R21** is MeDIC's own contribution and has no SEPIO counterpart; it must survive inside a
  single item rather than be modelled by SEPIO.

**R23–R25 cost nothing and are undocumented.** All three are satisfied by `minimal.yaml` as it
stands — an association-style host, an attribute-style host with two independently evidenced
slots, and a claim with no `statement_text` at all were each validated against the unmodified
kernel. The gap is guidance. The one real hole is D1's invented `_host:` key, which is the only
place in the corpus where the kernel genuinely cannot say what it needs to say (SPEC Q9).

**R25 is the sharpest of the new rows.** Not one `statement_text` in the corpus appears in any
source document — every one is a rendering of a structured triple that lives elsewhere (M1's is a
paraphrase of its own `id`). The slot sits one line away from `TextSpan.value`, which *is*
verbatim. Nothing marks the difference.

**R4 is universal.** Every single example needs a verbatim span attached to an identified
document. That is the kernel's core and it is right — with one qualification: N1's
`ConcordanceItem` and N2's unverified PMID pointer have no span, and forcing them into
`TextSpan` requires inventing one. This is the corpus's one argument for a **change to the
kernel's class list**, not just its enums.

**R11 is the load-bearing justification.** It is exercised by seven of nine examples, and it is
the requirement that actually justifies the item/line split — not item reuse (R8), which the
corpus shows is rare. But it sits entirely on the Track 2 side of the line, which is the tension
in SPEC Q3.

**R18 has never been exercised.** All 160,187 mondo-ai packets are UNREVIEWED and no example in
the corpus contains a real curation decision with a rationale. The claim that trust accumulates
across many weak interpretations is currently **untested against data**.

## Per-resource gap summary

| | DisMech | MeDIC | mondo-ai |
|---|---|---|---|
| Verbatim span + document | ✓ (validated exact) | ✓ (with char offsets) | partial (concordance has none) |
| Direction | ✓ (but conflated with strength and QC) | **✗** | ✓ (but cannot vary) |
| Strength | ✗ (folded into `PARTIAL`) | partial (`evidence.confidence` + `source_role`) | ✓ (but source constants) |
| Evidence source axis | ✓ (misused for document type) | two parallel vocabularies | ✗ |
| Interpretation provenance | **✗** (despite being AI-curated) | ✓ (agent + tool + version, pinned) | partial (synthesis only) |
| Item provenance | ✗ | ✓✓ (best in class) | partial |
| Synthesis | ✗ (prose only) | `reliability` (opaque rules) | ✓ (single-valued) |
| Curation state | invented parallel vocabulary (`Discussion.status`) | on one product only | ✓ (unused) |
| Aggregate that can vary | n/a | ✗ (always 1.0) | ✗ (always 1.0) |

## Suggested order of attack

1. **Add `direction` to MeDIC** (M2 data already exists). Largest semantic gain per unit effort
   anywhere in Monarch.
2. **Split DisMech's `supports` enum** via the existing `dismech_to_minimal` transform; drop
   `NO_EVIDENCE` / `WRONG_STATEMENT` from released data.
3. **Adopt a `basis` enum on every score** (MEASURED / DETERMINISTIC / PRIOR / SELF_REPORTED).
   Cheap, and turns R13 from a convention into a constraint.
4. **Resolve the `ConcordanceItem` misfit** with SEPIO — it blocks mondo-ai from being kernel
   compliant.
5. **Take R14, R15, R20 to Matt as questions**, with D2, D3 and M1 as the worked cases — and
   **Q8** with them: whether the base evidence item should be an extraction result (SPEC §7.2).
   N1 and N2 are the counter-cases, since neither concordance nor a consortium decision is an
   extraction of anything.
6. **Write the attachment guidance** (R23–R25). Zero schema change, and it removes the most
   likely way an adopter gets the kernel wrong: assuming `HasEvidenceLines` is the only way in,
   and reading `statement_text` as source text.
7. **Add a corpus validation test.** The `minimal:` blocks pass today; nothing keeps them
   passing.
