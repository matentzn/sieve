# Evolving DisMech's evidence model, one problem at a time

**Status:** draft · **Date:** 2026-08-28 · **Author:** Nico Matentzoglu

## Why this document exists

Chris's objection to the shared evidence model is that it is abstraction without a forcing
problem, and that each resource should build what its own requirements demand. I do not agree
with the conclusion, but the method he is asking for is the right one, so this plan adopts it:
**no step here is justified by SEPIO alignment.** Every step starts from a defect that costs
DisMech something today, is cited to an issue on the tracker, and carries a test that fails
before the change and passes after.

Where a step has no local justification and exists only for interchange, it says so and is
marked optional. There is exactly one such step, it is last, and it changes no data.

The staging matters as much as the content. #7439 already proposes the full SEPIO model as one
additive experiment. This plan decomposes that into steps that each stand on their own, so the
programme can be stopped at any point and still have paid for itself.

## What the tracker actually says

140 of 1,000 issues touch evidence or its representation. They fall into five clusters.

| Cluster | Issues | What it is |
|---|---|---|
| **Verification and integrity** | ~60, the largest by far | The verbatim-snippet guarantee does not hold for a measurable fraction of the KB |
| **Strength and study design** | #9421, #9710, #7439 | `evidence_source` records modality, nothing records how well the thing was studied |
| **Source kind vs document kind** | #8184, #6997, #7027, #6954 | `evidence_source` is doing double duty and curators disagree about it |
| **Claim to evidence linkage** | #9390, #7026 | A quantitative claim has no machine-readable link to the item that grounds it |
| **QC signal contamination** | #6224, #6955, #6431 | `NO_EVIDENCE` and mis-set `supports` sit inside the evidence list and inflate it |

Two things stand out. The verification cluster is much bigger than the modelling cluster, and it
is upstream of it. And #9421 and #9710 were filed independently, from two different curation
runs, asking for the same missing axis.

**Updated 2026-08-29.** The QC-contamination cluster is largely closed by PR #10003, and the
strength cluster has since been filed a further three times (#9785, #9951, and #9833/#9827 as
duplicates) — five independent filings of one gap, which is itself the argument for fixing it.
@cmungall has asked for the duplication to stop and for a path forward instead; this plan is that
path. A sixth cluster has opened that the table above does not cover: **source independence**
(#10029), where two papers from one laboratory were graded as independent confirmation.

## Measured baseline

Counted on my checkout at `f311ef9d6a` (2026-08-12), so these run below the numbers in #9421,
which was measured on a newer `main`. Percentages are stable.

| | count | share |
|---|---:|---:|
| Evidence items KB-wide | 109,886 | |
| `supports: SUPPORT` | 100,639 | 91.6% |
| `supports: PARTIAL` | 8,407 | 7.7% |
| `supports: NO_EVIDENCE` | 445 | 0.4% |
| `supports: REFUTE` | 395 | 0.36% |
| `evidence_source: HUMAN_CLINICAL` | 70,748 | 64.4% |
| `evidence_source: OTHER` | 18,741 | 17.1% |
| `evidence_source` unset | 8,131 | 7.4% |
| Reference is a PMID | 94,861 | 86.3% |
| Reference is DOI, ORPHA, trial, url or CGGV | 14,826 | 13.5% |
| Missing `reference_title` | 4,146 | 3.8% |
| Missing `snippet` | 57 | 0.05% |

Nine tenths of the corpus is one `supports` value and two thirds is one `evidence_source`
value. Neither field discriminates within the mass of the KB.

---

## Step 0: make the guarantee that already exists actually hold

**Scenario.** A curator adds an evidence item citing `DOI:10.1234/x` with a fabricated snippet.
`just validate-references` passes. `doi` is in `skip_prefixes` in
`conf/reference_validator_config.yaml`, so the snippet is never compared to anything (#7514,
5,158 items on my checkout). A second curator adds an item with a real PMID, a real snippet, and
a `reference_title` copied from a different paper. That also passes, because nothing compares
the title to the cache (#7536 check 1, #9713, #9519, #9138). A third file produces
`Total checks: 0` and is reported as clean (#7024, #9702, #7260).

**Change.** No schema change. Three validator fixes: fail closed when a file yields zero checks,
remove `doi` from the skip list and give it a fetch path, and add the title-versus-cache
comparison.

**Migration.** None. This is tooling only.

**Test that fails today.** Assert every file with at least one evidence item yields at least one
check. Assert the count of snippets outside the verbatim guarantee is zero.

**Cost.** Days. **Unlocks:** everything downstream. Each later step adds structure on top of
snippets, and structure inherits the reliability of what it is attached to. Adding a
`study_design` field to an item whose snippet was never checked buys nothing.

**Why first.** This is the cheapest step, it needs no migration, and it is the only step that
makes the KB's existing headline claim true. It is also the step Chris's argument most clearly
supports: it is pure local pain with no model change at all.

---

## Step 1 (SHIPPED, as direction + directness): split `supports`

**Outcome, PR #10003, merged 2026-08-29, closing #7439.** The split landed on a different second
axis than this step proposed. Reading the curators' own `explanation` prose across all 11,620
`PARTIAL` items showed the field was never carrying strength: it carried indirect support, an
inverted model system, one item making two claims, and simple irrelevance. So `supports` narrowed
to direction only — `SUPPORT` / `REFUTE` / `NO_EVIDENCE` — and the new axis is `directness`
(`DIRECT` / `INDIRECT` / `UNKNOWN`), with `PARTIAL` and `WRONG_STATEMENT` retired.

**The headline: self-contradictory `supports` gradings fell from 8,285 to 353**, a 96% drop, and
`supports` is now cleaner than `evidence_source` (715) for the first time.

The reason directness beat strength is worth carrying into the shared model: directness is
judgeable from the snippet and the claim alone, so two curators who disagree have something to
point at. Strength needs study design, sample size and replication — none of which the item holds.
Design decisions §12 holds that strength should be *derived*, not authored, and that is unchanged.

**One migration lesson worth carrying, because it cost something.** `PARTIAL` was not only a
dumping ground; several curators were using it to mean *reported secondhand*. Retiring it removed
that signal without replacing it, and the explanations were not migrated — 375 files still carry
"marked PARTIAL because…" prose describing a value the schema no longer has, four of them naming
secondhand citation as the reason (`Immunodeficiency_61.yaml:437` reads `supports: SUPPORT` above
an explanation that says it was marked `PARTIAL` for exactly that). The lesson is not that the
narrowing was wrong. It is that **before collapsing an overloaded field, enumerate what it was
carrying and give each meaning somewhere to go first** — the four meanings were enumerated, but
only three were rehoused.

The 11,620 migrated items carry `directness` **absent**, not defaulted — absent means unassessed,
and defaulting would have manufactured 11,620 appraisals no curator made. The population is
enumerated in `docs/reports/data/partial-evidence-directness-worklist-2026-08-29.tsv`, and the
4,130 lines of curator prose still reading "Marked PARTIAL because…" were deliberately kept: the
enum token is stale, the reasoning is not.

*Original framing, retained because Step 2 still rests on it:*

**Scenario.** From #9710: a curator marks abatacept evidence `PARTIAL` because the cited review
recommends for the CTLA-4/LRBA/DEF6 group while the claim is about DEF6 specifically. That is a
scope mismatch, not partial support. From #9390: a curator marks an item `PARTIAL` because the
9/12 fraction counts a facial gestalt rather than the individual feature. Also not partial
support. `PARTIAL` is absorbing at least three distinct meanings across 8,407 items.

**Change.** Add `direction` (`SUPPORTS`, `REFUTES`, `NEUTRAL`) and `strength`
(`STRONG`, `MODERATE`, `WEAK`). Keep `supports` as a deprecated alias for one release.

**Migration.** Mechanical. `SUPPORT` to `SUPPORTS`, `REFUTE` to `REFUTES`, `PARTIAL` to
`SUPPORTS` plus `strength: WEAK`.

**Test that fails today.** A round trip over the KB that reconstructs `supports` from
`direction` plus `strength` and diffs against the original. I have run this transform already:
1,615 of 1,639 disorder files round trip byte-identically, and every mismatch is `images` or a
snippet-less item, neither of which is about this split.

**Cost.** Days for schema and data. The real cost is the curation prompt, since `CLAUDE.md`
carries roughly ten worked YAML examples of the flat shape.

**Unlocks:** Step 2 has somewhere to put its answer, and `PARTIAL` stops being a dumping ground.

---

## Step 1b (PARTLY SHIPPED): get QC signals out of the evidence list

**Outcome.** `WRONG_STATEMENT` is gone — its single use in `Huntington_Disease.yaml` recorded that
the entry's own subtype name was inaccurate, the name has since been fixed, and the correction
moved to a `history/` record. `NO_EVIDENCE` was **kept**, and on reflection that is right: "this
source does not bear on the claim" is an evidential statement, not a QC flag, and PR #10003 fixed
a real exporter bug on exactly this point — `NO_EVIDENCE` was being emitted as SEPIO `neutral`,
which asserts something different (bears on the claim, favours neither side). Such lines now carry
no `direction_of_evidence_provided` at all.

What remains of this step is the inflation problem, now 353 mis-set `supports` values rather than
8,285 — a small enough set to gate in `check-snippet-grading`.

*Original framing:*

**Scenario.** From #6224, Shigellosis mechanism claims "rest on `NO_EVIDENCE` filler". An entry
with three evidence items, two of which are `NO_EVIDENCE`, reads to any consumer as three
citations. 445 items assert that the cited reference does **not** support the claim, and they
are counted as evidence.

**Change.** `NO_EVIDENCE` and `WRONG_STATEMENT` move out of `supports` into a curation-status
block on the item. They stay in the repository, and they stop being evidence.

**Migration.** 446 items, mechanical.

**Test.** No released evidence item carries a QC value in `direction`. Evidence counts per claim
change only for entries that had QC items.

**Cost.** Hours. **Unlocks:** any count or aggregate over evidence stops being inflated by
records that say the opposite of what they appear to say.

---

## Step 2: add `study_design` and `sample_size`

**Scenario.** From #9710, five items in two entries, all correctly `HUMAN_CLINICAL`:
a meta-analysis of 27 studies, an RCT with n=34, an open-label single-arm trial with n=30, a
case-control series with n=10 per arm, and a case report of 4 siblings. From #9421: the same
entry carries a dominant and a recessive inheritance block, each with one `SUPPORT` item. One
rests on several independent multi-patient series, the other on a single consanguineous pedigree.
They render identically, and a reader has to open the papers to find out which is better
supported.

**Change.** `study_design` enum and optional `sample_size`.

**Migration.** Partly automatic. PubMed `publication_types` is already stored in the reference
cache frontmatter, and carries `Randomized Controlled Trial`, `Meta-Analysis`, `Case Reports`,
`Practice Guideline` and `Review` directly. Backfill where the mapping is unambiguous, leave
unset otherwise, and measure the coverage rather than guessing at it.

**Test.** Report backfill coverage as a number. Assert no item claims a design its cached
`publication_types` contradicts.

**Cost.** Days plus a backfill run. **Unlocks:** the first axis that actually discriminates
within the 64% `HUMAN_CLINICAL` bucket. #9421 ranks this as the single highest-value addition,
and I agree.

**Note.** This axis does not exist in the microschema. It is a DisMech requirement first, and it
should be fed upward rather than borrowed downward.

**The live objection, and why it does not sink this step.** Design decisions §12, restated in
#10003, holds that strength should be derived rather than authored. That is an argument against a
curated `evidence_strength` grade — not against `study_design`, which is exactly the *input* a
derivation needs and which the reference cache already supplies. The step survives its own
objection provided the slot records a fact about the study, never a judgement about the claim.
#10029 adds the same argument from the other end: `authors:` is in the cache too, so independence
can be checked without curator judgement.

**Two refinements from the thread.** `replication` is doing more work than its rank suggests — for
a single-family Mendelian claim, "has anyone else seen this" *is* the classification, and it is
cheap and reliable to establish at curation time (APMR1: one family, seven affected, zero
replication in nine years, all of it recorded in prose). And the loss is not only that weak
evidence cannot be discounted: IRIDA's best causal evidence is a randomised placebo-controlled
Phase 1 trial that reads flat against the entry's n=1 items, so the missing metadata cannot
**promote** the item that deserves it. @cmungall's constraint stands and narrows the scope
usefully: much of the pathograph is not RCT-shaped, so this axis is for clinical statements, and
gene–disease validity should be sourced from ClinGen rather than re-derived here.

---

## Step 2b: mark citation distance

**Scenario.** From #10212, curating LTBP3: the only available source for a thoracic aortic
aneurysm claim was a case report's *discussion* relaying two families it had read about. The
snippet asserts the claim exactly, so there is no inference step — the reader is simply two
documents away from the patients. The curator marked it `directness: INDIRECT` and then explained
in prose that this was not what the slot means. Three items in one file, same misuse.

**Why it outranks strength.** Published quotation-error rates are 14.5–20%, two thirds of them
major. Relayed claims are where those errors accumulate, and unlike strength this is *mechanically
actionable*: if an item is marked as relayed with a traceable original, a validator can ask whether
the primary is cited in the entry, and `just fetch-reference` makes the upgrade a two-minute job —
the #10212 example was replaced with a firsthand report almost immediately. Nothing today can find
the others; grepping prose for the phrasing hits 47 places, which is a floor.

**Change.** Not a new enum. `StatementTraceability` in the microschema (SPEC §4.6) already carries
this, with ECO terms confirmed against OLS: `ECO:0000033` traceable, `ECO:0006016`
clinical-study-referenced, `ECO:0000034` untraceable. It needs one addition — a firsthand value —
and a scope widening from testimony to any text-derived item. A `primary_reference` belongs only
on the traceable value; requiring one on untraceable items would push curators toward guessing a
plausible primary, which is the fabrication surface the evidence-model docs exist to close.

**Do the free half first.** The schema's own `DirectnessEnum` comment already says directness "is
judgeable from the snippet and the claim alone", and citation distance fails that test — so the
misuse is already excluded by the schema, just not anywhere a curator reads. Copying that clause
into `CLAUDE.md` costs one edit and stops the next three entries being written wrong.

**And the detector, which needs no schema at all (#10262).** The structural signal that a quote is
relayed is already in the cache. NLM structured-abstract labels (`BACKGROUND:`, `RESULTS:`, …) are
present in 10,196 of 35,754 PMID files, and since a snippet must be an exact substring,
`body.find(snippet)` against the section boundaries computes the zone deterministically — no MeSH
heuristic, no LLM, no false positives from indexing lag. A second, complementary tier uses MeSH
(a `HUMAN_CLINICAL` item citing an animals-only paper) and catches the unstructured abstracts the
first tier is blind to; #10262 measured 207 such items across 61 files, and rightly calls it a
lower bound on a narrow slice rather than the size of the problem. Report at both tiers, tiered by
precision, and gate neither.

This is the step's real argument. The axis has been proposed three times independently
(`publication_role`, `claim_provenance`, `quote_role`) and stalled each time against §12's
derived-not-authored rule. It **passes** that rule — the zone is computed from the cache — which
is what none of the three filings established.

**Cost.** Documentation, hours. Slot, days. **Timing is unusually good:** `directness` is set on
213 of 147,550 items, and the three misuses above are not yet on `main`.

---

## Step 3: separate document kind from evidence source

**Scenario.** From #6997: one GeneReviews record, `PMID:20301360`, tagged `HUMAN_CLINICAL` on 42
evidence items and `OTHER` on 6, **within a single entry**. The curator normalised all 48 to
`OTHER`, was correctly told that made the entry a KB-wide outlier, and reverted. Both readings
are defensible because the field is answering two questions at once. From #8184: no rule for
review articles, and one PMID carrying two values. 18,741 items sit in `OTHER`, and a
substantial share of them mean "this is a review", which is a document kind, not a study kind.

**Change.** Add `document_type` on the reference. Narrow `evidence_source` to study modality
only, and write the rule down.

**Migration.** Backfillable from the same cached `publication_types` as Step 2.

**Test.** Assert no PMID carries two different `evidence_source` values across the KB. That
check fails today and is a one-line query.

**Cost.** Days. **Unlocks:** `OTHER` stops being a bucket for two unrelated things, and #6997
gets an answer instead of a convention argument that recurs.

---

## Step 4: link a claim to the evidence item that grounds it

**Scenario.** #9390 in full, and it is the best-argued issue on the tracker. 11,692 phenotypes
carry a frequency band. 10,462 of them have no fraction anywhere in their own evidence. 715 have
more than one fraction with nothing saying which grounds the band. Of the 388 that are
unambiguous, 30 contradict their own evidence. The author prototyped the obvious checker and
hand-verified five flagged cases: four were false positives, and each failed for a different
reason (the complement of the claim, a comparison arm, a composite feature, a different
construct entirely). The check is not viable because the link does not exist as data.

**Change.** Record the basis of the band alongside it:

```yaml
- name: Congenital heart disease
  frequency: FREQUENT
  frequency_basis:
    numerator: 10
    denominator: 15
    evidence_ref: <item id>
    population: MEGF8-associated CRPT2, pooled 2012 and 2024 series
```

**Migration.** None required. New claims fill it, old claims are backfilled opportunistically.

**Test.** A frequency checker that only runs where `frequency_basis` is present, and is therefore
precise rather than 20% precise. Coverage grows as a tracked number.

**Cost.** Days for the schema, ongoing for backfill.

**Unlocks.** This is the first step that puts structure *between* a claim and an item, and it is
where DisMech starts needing something line-shaped. It arrives from a local QC problem rather
than from a model.

---

## Step 5 (DECLINED upstream, for now): let several items form one argument

**Outcome.** PR #10003 explicitly did not adopt SEPIO's `EvidenceLine` / `DataItem` / `Document`
classes. The reasoning: an `EvidenceItem` already *is* an evidence line over one data item and one
document, and `linkml-reference-validator` supports `ELLIPSIS_INSERTION`, so a single `snippet`
can already carry a discontinuous multi-span quote — which was most of what the nesting bought.
SEPIO alignment is carried by `exact_mappings` on the native slots instead, keeping design
decisions §5's export-layer-only rule intact and sidestepping the vocabulary collision with #7612.

The cost is named honestly in the PR, and it is the strongest argument for revisiting:
`glymphatic_dysfunction.yaml` holds a REFUTE (an independent lab found no AQP4 effect) followed by
a rebuttal attributing that negative to anaesthetic regimen and tracer route. The second item is
aimed at the first, and a flat list records both against the node as parallel primary
observations. That is an undercutting defeater in DisMech's own data, and it is the case to bring
back rather than the grouping argument below.

One more empirical finding from the merge, which cuts against item reuse generally: entries that
define an evidence list once with a YAML anchor and reuse it by alias cannot carry a
claim-relative `directness` on the shared object, because directness is claim-relative and the
object is not. Reuse and per-claim annotation are in tension.

*Original framing:*

**Scenario.** From #9710: the DEF6 entry rests on seven patients from three kindreds across two
papers. The index paper and the two reviews that summarise it look identical in the YAML, but
only one is an observation. An entry with three citations reads as better supported than one
with one citation, whether or not the extra two are independent. From #7439: two snippets from
the same paper may be two arguments or one, and today there is no way to say which.

This is measurable. On the HABP2 example in the monarch_evidence corpus, eight items on one
claim, the same Net Evidence Ratio computed under four defensible groupings gives −0.250, 0.000,
−0.200 and 0.000. Two of those are on opposite sides of zero. Nothing about the curated
judgement changed.

**Change.** An optional grouping layer. Items stay exactly where they are; a group names a set of
them and carries the direction, strength and rationale for the argument they jointly make.

**Migration.** None. Ungrouped items behave as today, which is one argument each.

**Test.** Aggregate outputs are computed over groups. Two independent citations of one cohort in
one group count once.

**Cost.** Weeks, because it changes rendering and any scoring.

**Unlocks:** independence (the DEF6 problem), and the ability to say that a review summarising an
observation is not a second observation.

**Caveat that has to ship with it.** Once grouping exists, the grouping convention has to be
declared in the data, because the same evidence grouped differently yields different aggregates.
A record that does not say how it was grouped cannot be aggregated safely by a consumer.

---

## Step 6: connect the interpreter record we already keep to the evidence

**Scenario.** This step is mostly built. `history/` is an append-only session store with its own
schema (`src/dismech/schema/history.yaml`): 4,568 records for disorders, 4,207 of them carrying an
`ai_agent` actor with model and agent tool named — claude-opus-5 on 1,536, claude-opus-4-8 on 855,
claude-sonnet-5 on 817, gpt-5 on 439 — plus timestamps, PR and issue links, and the interpretation
reasoning in prose, including suggestions declined and why. Against the wider corpus that is
unusually good: MeDIC has no interpretation step at all, and mondo-ai records it only on synthesis.

What is missing is one link. The store's finest grain is `sections:` (phenotypes, treatments,
genetic), `EvidenceItem` still carries its seven original slots, and no session id appears in
`kb/`, so the join runs one way. We can ask what happened to an entry; we cannot ask which reading
produced a given snippet. #7835 is why that matters — fabricated *verification notes* justifying a
wrong call, an interpretation with no accountable author — and #6211 tracks the Falcon deep
research provenance stubs.

**Change.** Carry the session id down to the group from Step 5 (or to the item until Step 5
lands). The agent, model and date are already recorded; this points at them rather than repeating
them.

**Migration.** A pointer slot on new records. Backfill is unusually tractable for a retrofit,
because the history records already carry timestamps and PR links: an entry's items can be
attributed to the session that last touched their section without reading a single diff.

**Test.** Given a discredited agent run, list every claim that depends on it. Today that resolves
to the entry and section; after this step it resolves to the evidence item.

**Cost.** Small — one slot and a backfill script, not a new provenance model. **Unlocks:**
targeted recuration instead of KB-wide sweeps, and the model spread above becomes queryable as a
covariate on claim quality.

**Caveat on what the store is worth.** `just validate-history` checks a record's *shape*, never
its `details` prose against the entry it describes. A false claim about what was curated is
therefore permanent, schema-valid and CI-passing — worse than a stale comment, because history is
append-only. Before leaning on this store as provenance, it needs the same treatment
`check-source-defect-claims` gave caches: an assertion about an artifact, checked against the
artifact.

---

## Step 7: mark contested attribution

**Scenario.** From #9710: in the DEF6 index report, two of three patients also carried a
homozygous pathogenic `SKIV2L` variant, whose own disease overlaps the digestive and cardiac
features the report attributed to DEF6. The second report says so explicitly. Today the only
home for this is a prose `KNOWLEDGE_GAP` discussion, so anyone reading the pathophysiology nodes
gets the unqualified version.

**Change.** A way to attach "this evidence is contested as bearing on this claim" to the claim or
the group, distinct from evidence that the claim is false.

**Cost.** Design first, then weeks. This is the least well understood step and should not be
attempted before Step 5.

**Unlocks:** the DisMech `Discussion` kinds `HUMAN_MODEL_MISMATCH` and `CONTROVERSY` get a
machine-readable form instead of prose.

---

## Step 8 (optional, no local justification): annotate for interchange

**Scenario.** There is none inside DisMech. Nothing in the tracker asks for this and no curator
is blocked by it.

**Change.** Add `class_uri` and `slot_uri` annotations to the classes and slots that Steps 1 to 7
produce, so instances are readable as SEPIO evidence without importing SEPIO and without changing
a byte of data.

**Cost.** Hours. Zero data migration, zero curation impact.

**Why it is here at all.** After Steps 1 to 7, DisMech has independently arrived at direction,
strength, document type, grouping and interpretation provenance. At that point the annotation is
a label on work already done, and the argument for it is that other Monarch resources can read
DisMech evidence without a bespoke parser. If that is not worth an afternoon, skip it. **This is
the step Chris's objection lands on, and he is right that it must not drive the ones above it.**

---

## What is deliberately not in this plan

- **No migration off the flat list.** Steps 1 to 4 keep the current shape. Step 5 adds a layer
  above it rather than replacing it.
- **No scoring policy.** Which weights, which thresholds, and what a number means is governance,
  and none of it is settled while independence and supersession are unrepresentable.
- **No `EvidenceLine` class in the schema before Step 5.** #7439 proposes it directly; this plan
  reaches the same place through four cheaper steps that each pay for themselves.
- **Nothing that requires the microschema to be finished.** Steps 0 to 7 are DisMech-local.

## Sequencing and a stopping rule

```
Step 0  verification holds          days      no schema change
Step 1  direction + directness      SHIPPED   #10003, 11,620 items migrated
Step 1b QC signals out              PARTLY    WRONG_STATEMENT gone; NO_EVIDENCE kept
Step 2  study design + n            days      partly auto-backfilled
Step 2b citation distance + zone    hours     docs, then a report-only detector
Step 3  document type               days      partly auto-backfilled
Step 4  claim to evidence link      days      no migration
Step 5  grouping                    DECLINED  revisit via evidence-about-evidence
Step 6  join history to evidence     days      backfillable from history/
Step 7  contested attribution       weeks     design first
Step 8  interchange annotation      hours     optional, zero data change
```

Steps 0 to 4 are independently valuable and none of them commits DisMech to anything. If the
programme stops after Step 4, DisMech has a verified corpus, a strength axis that discriminates,
a clean source axis, and checkable frequency bands, and has given up nothing.

Step 5 is the first real commitment, and it should not be taken until Steps 0 to 4 have shipped
and the independence problem in #9710 has actually bitten someone twice.

## Open questions

1. **Does `study_design` belong on the item or the reference?** A paper has one design; an item
   quotes one paper. Putting it on the reference deduplicates it across the 94,861 PMID items,
   at the cost of a lookup. Probably the reference, since the cache is already the home for
   `publication_types`.
2. **What happens to `PARTIAL` items that were scope mismatches?** Step 1 maps them to
   `SUPPORTS` plus `WEAK`, which is wrong for the #9710 abatacept case. Either accept the
   imprecision and fix by hand later, or add a scope slot in Step 1 and do it once.
3. **Is the frequency link in Step 4 a special case, or the general claim-to-item link?**
   Prevalence (#8431, #7005), penetrance and onset have the same shape. Building it once as a
   general basis mechanism is probably right, but #9390 is the only fully worked case.
4. **Who owns the grouping convention decision in Step 5?** It cannot be per curator, and the
   monarch_evidence corpus shows the naive rule (group by direction, strength, source and
   document) destroys real structure on HABP2 by merging three distinct arguments from one paper.

## Related

- Issues: #7439, #9421, #9710, #9390, #7514, #7536, #6997, #6955, #6224, #8184, #9713, #7024
- [`SPEC.md`](SPEC.md) for the model these steps converge on, and for the requirements DisMech
  would contribute upward (`study_design` and `sample_size` are not in it today)
- [`../transform/`](../transform) for the Step 1 migration, already written and tested
