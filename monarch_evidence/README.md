# monarch_evidence

Evidence modelling for Monarch: one SEPIO-aligned semantic foundation, two profiles — a small
embeddable **microschema** every resource can adopt, and a richer **SEPIO Monarch / SIEVE**
profile for projects that need evidence calculus — plus a corpus of nine real records from
DisMech, MeDIC and mondo-ai that shows what each profile has to support.

This folder is the design and analysis home for that programme. The schemas it specifies live in
the same repo: [`../schema/minimal.yaml`](../schema/minimal.yaml) (Track 1),
[`../schema/sieve.yaml`](../schema/sieve.yaml) (Track 2), and
[`../transform/`](../transform) (the linkml-map bridge). The originating notes are in the
`~/ws/notes/evidence` thinking repo.

## Files

| Path | What it is |
|---|---|
| `README.md` | this index |
| `SPEC.md` | **the specification** — purpose, the two tracks, the core SEPIO axis, the evidence/provenance/data-quality split, requirements R1–R22, per-resource adoption path, open questions and blockers |
| `examples/README.md` | **detailed walkthrough of all nine examples**, grouped by resource, with what each one proves |
| `examples/dismech/d1-attr-amyloidosis-multilevel.yaml` | ATTR amyloidosis — evidence attached to a hypothesis group, a node and a causal edge; one paper used four times with four snippets |
| `examples/dismech/d2-habp2-contested-claim.yaml` | HABP2 p.G534E — a genuinely contested claim, 3 supporting vs 5 refuting items, three distinct arguments from one document, no aggregation |
| `examples/dismech/d3-adsa-undercutting-defeater.yaml` | ADSA `Discussion` — an argument that a mouse model is *inadmissible* as evidence, plus prospective experiments |
| `examples/medic/m1-exenatide-multijurisdiction.yaml` | Exenatide × T2DM — six regulatory documents, four jurisdictions, noisy-OR corroboration with no notion of independence |
| `examples/medic/m2-zolmitriptan-limitation-and-scope.yaml` | Zolmitriptan — an explicit "not indicated for" sentence with no slot, and a scope narrowing every quality gate scores 1.0 |
| `examples/medic/m3-gemifloxacin-transformation-chain.yaml` | Гемифлоксацин → CHEBI:101853 — a four-step transformation chain, and why its confidence is not belief |
| `examples/mondo-ai/n1-lecd-concordance.yaml` | OMIM + ORDO + DOID concordance — line scores that are source constants, an NER stuck at 1.0 |
| `examples/mondo-ai/n2-provenance-as-evidence.yaml` | Consortium decision + ORCID + candidate PMID turned into evidence lines with trust levels |
| `examples/mondo-ai/n3-ai-synthesis.yaml` | LLM synthesis — self-reported confidence stored as a score; synthesis that cannot be disputed |
| `analysis/requirements-matrix.md` | traceability matrix: requirement × example, what is met where, and a suggested order of attack |
| `analysis/source-model-comparison.md` | side-by-side reading of the three source schemas as they exist today |

## Start here

- Want the plan → `SPEC.md`
- Want the evidence for the plan → `examples/README.md`
- Want to know what to do first → `analysis/requirements-matrix.md` (last section)

## The four things to take to SEPIO

1. **Supersession (R14).** Later evidence that reverses earlier evidence is not just another
   vote. D2 (HABP2) and DisMech's ALS/AMX0035 record both break a naive tally.
2. **Undercutting defeaters (R15).** "That evidence does not bear on this claim" is categorically
   different from "that evidence refutes this claim". D3 is the worked case, and it is the
   strongest argument in the corpus for the normalised representation.
3. **Source independence (R20).** Corroboration arithmetic that cannot tell two republications
   of one authority from two independent authorities inflates confidence mechanically. M1 and N1
   show it from both sides.

4. **Is the base evidence item an extraction result (Q8)?** Matt's relayed proposal makes every
   first-order item a data extraction result pointing at a data item pointing at a document.
   SPEC §7.2 argues against inverting the hierarchy — N1's concordance and N2's consortium
   decision are not extractions of anything — and proposes the A/C split plus a profile
   constraint instead. First clarify what the intermediate level is meant to hold; the relay
   collapses `DataItem` into `Document` and that may be a transmission error rather than the
   proposal.

Plus one kernel change and one cheap win: `ConcordanceItem` does not fit the microschema's
`TextSpan`-only item range (N1), and a `basis` enum on every score
(MEASURED / DETERMINISTIC / PRIOR / SELF_REPORTED, stolen from MeDIC) would turn the
data-quality-vs-evidence-strength rule from a convention into a constraint.

## Status

Draft, revised 2026-08-16. Third revision adds the evidence-kind survey across all four schemas
(SPEC §4.4, twenty kinds), the item taxonomy separating SEPIO conceptual classes from Monarch
extension classes with `TextDerivedEvidenceItem` in place of `TextSpan` (§4.5), and the shared
enum register (§4.6). Expert review moves from an item to an `EvidenceLine`, which opens Q11.

Second revision added the host-statement model (SPEC §3.2, R23–R25),
the evidence / provenance / quality attachment picture (§7.1), the argument against making the
base evidence item an extraction result (§7.2, Q8), and R26's resolution — where the ordered
snippet→ontology grounding chain lives, and why SEPIO's native provenance slots cannot hold it
(§7.3).

The corpus is now **executable and tested** — `tests/test_monarch_evidence_corpus.py` validates
every `minimal:` block against `../schema/minimal.yaml`. Nine of fourteen pass outright; the
five that fail do so only on `EvidenceSource: REGULATORY` and `DocumentType: REGULATORY_LABEL`,
the two values the corpus marks PROPOSED and the SPEC tracks as Q7.

The SPEC states my current understanding of the plan from the team notes;
inferred points are flagged `[inferred]` and genuinely open ones are in SPEC §10 rather than
silently resolved. The corpus is complete and every `as_is` block is real data or real code —
sections reconstructed from code rather than stored data carry a `provenance_note`.
