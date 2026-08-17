# The Monarch evidence corpus

Nine real records from three Monarch resources, each transcribed as-is and then re-expressed in
both profiles of the [SPEC](../SPEC.md). Built in response to Matt Brush's request (Slack,
2026-08):

> Would it be worthwhile to assemble and work through a corpus of diverse examples of DisMech
> claims that vary in the complexity and nuance of their evidence and provenance — so that we
> can more comprehensively/systematically understand the scenarios a SEPIO-based model would
> need to support, and evaluate the value a more normalized representation might offer?

Widened beyond DisMech deliberately: DisMech alone would have produced a corpus of flat
literature-snippet lists and missed entire categories — regulatory attestation, transformation
provenance, cross-ontology concordance, AI synthesis, and agent trust.

## How to read a file

Every example is one YAML file with the same sections:

| Key | What it holds |
|---|---|
| `id`, `title`, `source`, `challenges` | identification and the requirement IDs (R1–R22) it exercises |
| `provenance_note` | present when the record is reconstructed from code rather than copied from stored data — read it, it matters |
| `summary` | what is interesting, in prose |
| `as_is` | the record as the resource stores it today, verbatim (trimmed with `…`, never paraphrased) |
| `minimal` | the same content in the Track 1 microschema |
| `sepio_monarch` | the same content in the Track 2 SIEVE profile, including slots that **do not exist yet** — those are marked `PROPOSED` |
| `gaps` | what breaks, what is lost, what neither profile can say |

Anything marked `PROPOSED` is a proposal for discussion, not an existing slot. Everything in
`as_is` is real.

**Identifiers.** MONDO/CHEBI/HGNC CURIEs in the rendered blocks were checked against OLS or taken
from the source record. ECO codes were **not** invented: where a code would be needed and none was
confirmed, the field reads `<TODO — needs OLS lookup…>`, which is also the spec's blocker B2 in
miniature. `ECO:0000305` (D1) is verified.

## The corpus at a glance

| ID | Resource | One-line hook | Headline problem |
|---|---|---|---|
| [D1](dismech/d1-attr-amyloidosis-multilevel.yaml) | DisMech | ATTR amyloidosis: evidence on a hypothesis, a node, and an edge | multi-granularity attachment; one paper used four times |
| [D2](dismech/d2-habp2-contested-claim.yaml) | DisMech | HABP2 G534E: 3 supporting vs 5 refuting | no aggregation; one document, three arguments; supersession |
| [D3](dismech/d3-adsa-undercutting-defeater.yaml) | DisMech | The Rnf170-null mouse models the *wrong* disease | undercutting defeaters have no representation anywhere |
| [M1](medic/m1-exenatide-multijurisdiction.yaml) | MeDIC | Exenatide/T2DM across 4 regulators, 6 documents | corroboration without independence; three different "confidence"s |
| [M2](medic/m2-zolmitriptan-limitation-and-scope.yaml) | MeDIC | "not indicated for prophylaxis" with nowhere to go | no `direction` slot; a silent scope narrowing scored 1.0 |
| [M3](medic/m3-gemifloxacin-transformation-chain.yaml) | MeDIC | Гемифлоксацин → CHEBI:101853 in four steps | ordered chain vs unordered bag; confidence ≠ belief |
| [N1](mondo-ai/n1-lecd-concordance.yaml) | mondo-ai | OMIM + ORDO + DOID all say "LECD" | line scores are source constants; NER is stuck at 1.0 |
| [N2](mondo-ai/n2-provenance-as-evidence.yaml) | mondo-ai | "The consortium included this term" as an evidence line | provenance counted as evidence; circularity |
| [N3](mondo-ai/n3-ai-synthesis.yaml) | mondo-ai | An LLM reads the packet and returns a verdict | self-reported confidence stored as a score; synthesis cannot be disputed |

---

## DisMech

DisMech's model is the closest thing Monarch has to a shared evidence vocabulary today: a flat
`evidence:` list attachable to almost any object, where each `EvidenceItem` carries
`reference`, `reference_title`, `supports`, `evidence_source`, `snippet`, `explanation`. The
snippet is validated to be an exact substring of the cited abstract, which makes DisMech evidence
unusually verifiable. What it lacks is any notion of who did the interpreting — despite being an
AI-curated resource.

### D1 — ATTR amyloidosis: three attachment levels, one paper four times

A single disease file attaches the *same item shape* at three levels: a `mechanistic_hypotheses`
group, a `pathophysiology` node, and a `downstream` causal edge. That is a strength — the
kernel's `HasEvidenceLines` mixin exists precisely so a host can graft evidence onto its own
containers without the schema imposing one — and the transform is mechanical.

The interesting part is PMID:25604431, which appears four times with four different snippets and
four different explanations, backing four different claims. This is the empirical answer to
Sierra's objection about item reuse: in practice pipelines **mint, they do not reuse**. Under
Track 1 the four spans are four legitimately distinct `TextSpan`s that share a `Document` id, so
nothing is wrong — but the reuse capability the item/line split was partly justified by is going
unused. The justification that *does* survive contact with the data is interpretation
provenance (R11), and the spec should lean on that one.

Also visible: `evidence_source: OTHER` used to mean "this is a review article". That is a
`DocumentType`, not a study kind. The two axes are conflated in the data even though DisMech's
schema separates them, and any ECO binding has to survive that.

The hypothesis groups (`CANONICAL` vs `EMERGING`, and edges tagged with the group they belong
to) are claim grouping, not evidence grouping. Neither profile has a home for it.

### D2 — HABP2 G534E: the case for evidence synthesis

The HABP2 replication controversy is the best single argument in the corpus for Track 2. Eight
evidence items on one node: three SUPPORT (the 2015 NEJM report's functional assay, its
case-control frequency argument, and one independent kindred series) and five REFUTE (four
independent groups on three logically distinct grounds, plus a review-level synthesis). DisMech
records the verdict three times in three places — prose in the node description,
`mechanism_confidence: HYPOTHETICAL`, and `status: DEPRECATED` on the hypothesis group — and
none of them is machine-derivable from the evidence list.

Three things this example forces:

1. **Synthesis must be an object (R9).** A consumer reading the YAML sees 3 vs 5 and cannot
   defensibly combine them. `EvidenceSynthesis` with a summary, a score, a named method and
   cited lines is the minimum.
2. **One document can carry several independent arguments (R8).** PMID:26745718 refutes on
   segregation, on population frequency, and on tissue expression. Under the agreed grouping
   rule (group by direction + strength + source + document) these would *wrongly merge into
   one line*, because the rule has no term for "different reasoning". The escape clause needs
   to be explicit and testable or extraction pipelines will destroy real structure.
3. **Supersession is not representable (R14).** Every refutation postdates the claim, and the
   2020 review is a synthesis *of* the refutations, not an eighth independent vote. Counting it
   as one more REFUTES line double-counts.

### D3 — ADSA: an argument about admissibility, not about truth

DisMech's `Discussion` object, kind `HUMAN_MODEL_MISMATCH`. The `Rnf170`-null mouse develops an
ADSA-like sensory phenotype — apparently strong `MODEL_ORGANISM` support for a loss-of-function
mechanism. The discussion argues it is not admissible: heterozygous human null carriers are
unaffected and homozygotes get a *different* disease, so the null mouse corresponds to the
recessive condition, not the dominant one.

This is an **undercutting defeater**: not "the claim is false" but "that evidence does not bear
on this claim". Conflating it with counter-evidence corrupts any aggregation — a naive NER would
count it as one more REFUTES line about the mechanism, when its actual effect is to *remove* a
SUPPORTS line from the tally. SEPIO's nesting (a Statement whose subject is an EvidenceLine) is
the natural home, and this is the strongest case in the corpus for keeping the normalised
representation. Whether it is legal in SEPIO, and what the pattern is, is SPEC Q5 — the first
thing to put in front of Matt.

Two secondary observations. First, the same human-genetics span is tagged `REFUTE` relative to
the ADSA mechanism claim but *supports* the discussion's own conclusion — direction is only
meaningful relative to a named target, which is why direction lives on the line and not on the
item. Second, `proposed_experiments` with `would_support` describe evidence that does not exist
yet; that is a research-agenda object with no home in either profile.

Also worth knowing, though not written up as a fourth example: DisMech's ALS record for AMX0035
carries one SUPPORT item (phase-2 CENTAUR, positive) and two REFUTE items (phase-3 PHOENIX,
negative; and the 2024 market withdrawal). A naive tally says 1:2. The truth is that the phase-3
result *supersedes* the phase-2 result and the withdrawal is a consequence, not a third vote.
Same R14 gap, in its most everyday form.

---

## MeDIC

MeDIC inverts DisMech: exemplary provenance, essentially no evidence model. Its core abstraction
is the **transformation chain** — a source string becomes a canonical id through named, typed,
contiguous steps, replayable byte-identically from git-tracked SSSOM/Babelon decision stores.
Its question is *how did this string become this ID*, not *should I believe this claim*. The
analysis in `medic/docs/sepio-sieve-alignment.md` is the best existing statement of the
evidence/provenance/data-quality boundary and the SPEC adopts it wholesale.

### M1 — exenatide × type 2 diabetes: corroboration without independence

Six `SourceAssertion`s — one per source *document* — from FDA/DailyMed, EMA (Bydureon and
Byetta), CDSCO India and PMDA Japan (two review reports). Each assertion is internally
single-source by construction: drug mention, disease mention and spans all come from that one
document. This is the cleanest mapping in the corpus: one assertion → one `EvidenceLine`, one
span → one `TextSpan`, the document → `Document`. MeDIC arrived at the kernel's own "one line per
source document" guidance independently.

Two problems.

**Independence (R20).** The pair-level noisy-OR treats six documents as six independent
corroborations and reaches 0.999998. But two of them are one authority (EMA) reviewing one
dossier lineage under two brand names, and two more are two milestones of one Japanese
registration. The effective count is four authorities, not six documents. Meanwhile MeDIC's own
`reliability` tier for the same pair is MEDIUM. Both numbers are reported and they disagree,
because they measure different things — and neither is an evidence-strength judgement.

**Three things called "confidence".** `confidence.overall: 0.999998` (pair, data quality),
`assertion.confidence.overall: 0.9` (linking fidelity) and `evidence.confidence: HIGH` (an
actual evidence judgement) share a word. Only the last maps to `strength_of_evidence_provided`.
Mapping either of the first two onto a line score would silently convert "we're unsure of the
identifier" into "the evidence is weak" — the single most dangerous integration error available.

`source_role: PRIMARY | INTERMEDIARY | NON_REGULATORY` is a real evidence-strength signal (the
regulator itself beats a republisher) with no home in the kernel. It should feed
`strength_of_evidence_provided` together with `evidence.confidence`.

### M2 — zolmitriptan: the REFUTES that has nowhere to go

Two defects in one record, both invisible to MeDIC's own quality machinery.

The label reads "migraine with **or without** aura". The extractor emitted "migraine with aura"
and grounded it to MONDO:0005475 — a narrower disease than the label licenses. Every step is
`quality: verbatim` / `lexical_exact` at `confidence: 1.0`, no `scope_narrowed` flag fires, and
the record's `reliability` is HIGH. Nothing is individually wrong: the output string *is* a
substring of the input. The error exists only in the composition. **Per-step confidence does not
compose into claim correctness, and a product of 1.0s can still be wrong** — which is also the
argument for keeping a human-readable verbatim span on every item, because a curator spots this
in one second.

The same section carries a `LIMITATION_STATEMENT` span: *"Zolmitriptan … are not indicated for
the prophylactic therapy of migraine or for the treatment of hemiplegic or basilar migraine."*
MeDIC deliberately types this role and keeps it out of the positive claim's negation scope —
real engineering effort spent on data it then has no slot to express. It is the one genuinely
REFUTES-shaped signal in the product.

The correct Track 1 rendering is **not** a REFUTES line on the indication statement. "Indicated
for X" and "not indicated for prophylaxis of X" are different propositions with different
predicates; the limitation becomes a REFUTES line on *separate statements*. Collapsing
contraindications or limitations into REFUTES on the indication is the trap flagged as hazard H3
in the MeDIC analysis.

And a bonus: that single sentence refutes at least three distinct statements. This is the item
reuse case (Q2) that *does* occur naturally — one data item, three interpretations, three
targets. Worth showing Matt as the counterexample to "reuse never happens".

### M3 — gemifloxacin: the chain, and why it must not be flattened

`Гемифлоксацин` → `Gemifloxacin` → `CHEBI:101853`, in four steps: a verbatim structured-field
read (`confidence_basis: DETERMINISTIC`), a DeepL translation via babelon 0.3.6
(`confidence_basis: PRIOR`, `flags: [unreviewed_machine]`, `status: CANDIDATE`), a lexical
grounding (`MEASURED`), and an identity normalization (`DETERMINISTIC`). Aggregate 0.855.

None of this is evidence. Under the SPEC §7 test it is provenance and data quality, and Track 1
correctly drops all of it, keeping one line: the Russian MoH registered this product.

The structural point is **set vs sequence**. MeDIC's `pipeline` is an ordered list with an
equality constraint between adjacent elements (`pipeline[n].output_value ==
pipeline[n+1].input_value`); SEPIO's `has_evidence_items` is an unordered bag. The only safe
mapping keeps the chain intact inside a *single* item. Decomposing it into sibling items
discards the contiguity guarantee the whole provenance model exists to provide — and would
scatter it across two different SEPIO item classes (`TextMiningResult` for
extraction/translation, `ConcordanceItem` for grounding/normalization) with nowhere to record
the ordering between them.

One idea worth stealing upward: `confidence_basis: MEASURED | DETERMINISTIC | PRIOR`. Being
forced to say whether a number was measured, is trivially 1.0, or is an assumed constant is a
discipline SEPIO lacks — and would immediately expose that an AI interpreter's self-reported 0.9
(N3) is a PRIOR wearing a MEASURED's clothes.

---

## mondo-ai

mondo-ai is already on SIEVE/SEPIO and is the only resource in the corpus that produces packets
in the target model. That makes its gaps the most informative: they are what remains wrong
*after* adopting the model.

### N1 — LECD: what 160,187 packets actually look like

Three source ontologies each carry "LECD" as a synonym, so the packet gets three evidence lines,
each holding one `ConcordanceItem`. Store-wide: 160,187 packets, 155,004 with exactly one line,
and every one of the 165,818 evidence items is a `ConcordanceItem`. All packets are UNREVIEWED.

Three things to notice.

**The line score is a source constant.** `scoreOfEvidenceProvided: 0.95` is OMIM's configured
reliability weight, applied identically to every OMIM-derived line in the store. It is a prior
about the *source*, not an assessment of *this* synonym. That is defensible — it is exactly the
"declared, revisable trust in a source" the vision calls for — but it belongs on the agent as a
trust declaration (R12), not silently in the per-line score slot, or it will be read as "this
synonym is 95% right".

**NER is degenerate.** Nothing in the concordance mechanism can emit a `disputes` line, so NER is
identically 1.0 across the entire store. A metric that cannot vary is not a metric. This is the
same defect as MeDIC's (hazard H4) arriving from the same cause: no direction diversity.

**Absence is silent (R20).** A source that lacks the synonym contributes no line, so "3 of 3
sources agree" and "3 of 12 sources agree" are indistinguishable. Concordance needs a
denominator.

There is also a genuine kernel misfit here. A `ConcordanceItem` has `sourceSubject` and
`mappingJustification` but no `value` and no `reported_in` — it is not a text span. The
microschema's `has_evidence_items` currently ranges over the concrete `TextSpan`, so expressing
concordance requires inventing a quote. **This is the one place where the kernel needs a change,
not just a mapping**: either a second concrete item shape, or `has_evidence_items` ranging over
the abstract `EvidenceItem`. Raise with SEPIO.

### N2 — provenance turned into evidence

Mondo axiom annotations carry `oboInOwl:source` strings. `MondoExtractor` regexes ORCIDs and
PMIDs out of them and turns each into an evidence line: consortium membership becomes an
`AgentContribution` with `trust_level: authority` and score 0.6; an ORCID becomes a curator
contribution at 0.8; a PMID becomes a `SieveDocument` marked "candidate — not yet verified" at
0.4.

Apply the SPEC §7 test to the consortium line: does "the Mondo consortium included this term"
survive if the synonym turns out to be wrong? Yes — the decision still happened. So it is
provenance. But would an expert who trusts the pipeline completely still want to see the ORCID?
Also yes. The test gives conflicting answers, and the reason is that **testimony is a real
evidence kind**: an expert determination is testimonial evidence, while an organisational
inclusion decision is provenance. mondo-ai treats them identically, as `AgentContribution`s
differing only in a weight, and that is the distinction worth drawing.

The consortium line is also **circular**: "the term is in Mondo" is being used as evidence for
"the term should be in Mondo", and at 0.6 on a 0–1 NER it carries a packet most of the way to
the 0.7 ACCEPT threshold before anyone has read anything.

Finally: `TextSpan.value` is required, so an unverified PMID pointer cannot be expressed in
Track 1 at all without inventing a quote. Either the kernel gains a citation-only shape, or —
better — such pointers simply do not enter the evidence model until enrichment extracts a span.
A PMID with no quote is a promise of evidence, not evidence.

### N3 — AI synthesis, and the number the whole vision rests on

The pipeline's end state, and the concrete instance of the claim that weak trust in individual
AI interpretations accumulates into something defensible. A packet gets concordance lines, then
PubMed enrichment adds a `SieveDocument` line with a real quote, then a `SynthesisAgent` reads
the whole packet and returns `{action, confidence, summary, key_evidence}`. That becomes an
`EvidenceSynthesis` carrying a `CurationActivity` that names the model and the prompt version.

Two things are right: the synthesis is a first-class object with provenance, and ADD/CONFIRM →
`supports`, REJECT → `disputes`, REVIEW → `neutral` is a sensible mapping.

Two are wrong, and both matter more than anything else in the corpus.

**The model's self-reported confidence is stored as a `Score`.** `Score(value=0.95,
description="AI confidence score")` sits in the same slot type as a computed NER, and no
consumer can tell them apart. Per the vision, the number that should drive curation is not the
model's opinion of itself but the *organisation's declared trust in that interpreter* — Opus
65%, Sonnet 56% — a human judgement, dated, attributed, and revised through deliberation.
Nothing records it. `AgentContribution.trust_level` exists but is a four-value enum with no room
for a numeric, dated, attributed declaration.

**Synthesis cannot be disputed.** `evidence_synthesis` is single-valued. Two interpreters reading
the same packet and disagreeing cannot both be recorded — which is precisely the scenario the
accumulation argument depends on. Either synthesis becomes multivalued, or an AI verdict becomes
an `EvidenceLine` in its own right, taking the packet's other lines as its items. The latter is
more SEPIO-shaped and lets one verdict become evidence for a later one.

---

## What the corpus establishes

1. **Direction is the biggest single win available.** MeDIC has none; mondo-ai's cannot vary.
   Both compute aggregates that are mathematically incapable of moving. Adding `direction` and
   populating it from data that already exists (`LIMITATION_STATEMENT` spans, DisMech `REFUTE`
   items) changes more than any other single slot.
2. **The three-way evidence / provenance / data-quality split is not academic.** M1, M2, M3 and
   N2 each contain at least one number or field that would be catastrophically misread if
   mapped to the wrong one.
3. **The normalised representation earns its keep at D3 and N3**, not at D1. The argument for
   separate items and lines is *not* item reuse (which the corpus shows barely happens, with M2
   as the honourable exception) — it is that interpretation is a separate act with its own
   agent, its own date, its own method, and its own defeasibility.
4. **Three requirements have no representation anywhere**: supersession (R14), defeaters (R15),
   and source independence (R20). All three are needed to compute an aggregate that is not
   misleading, and all three should go to SEPIO as questions rather than being invented locally.
