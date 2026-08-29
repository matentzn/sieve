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

## Step 1: split `supports` into direction and strength

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

## Step 1b: get QC signals out of the evidence list

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

## Step 5: let several items form one argument

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

## Step 6: record who did the interpreting

**Scenario.** DisMech is AI-curated and records nothing about the interpreter. #7835 documents a
new failure mode: fabricated *verification notes* that justify a wrong call, which is an agent
producing a plausible interpretation with no accountable author. #6211 tracks Falcon deep
research provenance stubs. When a claim is later found wrong, there is no way to ask which agent,
model or prompt version produced the reading, and therefore no way to find the other claims it
touched.

**Change.** `interpreted_by` on the group from Step 5 (or on the item until Step 5 lands):
agent, date, model or prompt version.

**Migration.** New records only. Backfill from git history where the curating agent is
recoverable.

**Test.** Given a retracted paper or a discredited agent run, list every claim that depends on
it. That query is impossible today.

**Cost.** Days for the schema. **Unlocks:** targeted recuration instead of KB-wide sweeps.

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
Step 1  direction + strength        days      mechanical migration
Step 1b QC signals out              hours     446 items
Step 2  study design + n            days      partly auto-backfilled
Step 3  document type               days      partly auto-backfilled
Step 4  claim to evidence link      days      no migration
Step 5  grouping                    weeks     no migration
Step 6  interpretation provenance   days      new records only
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
