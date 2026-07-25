# One Evidence Model to Rule Them All

*A proposal to the Monarch tech team — speaker script + slides*
*Nico Matentzoglu · 2026-07-12*

> How to use this file: each block is one slide. **On screen** is what the audience
> sees (keep it sparse). **Say** is the script — roughly what I'll actually say, in my
> voice. Timings assume ~18–20 minutes plus discussion. Cut slides 7–8 to the appendix
> if we're short.

---

## Slide 1 — Title

**On screen:**
- **One Evidence Model to Rule Them All**
- Consolidating how Monarch records *why we believe things*
- Nico Matentzoglu

**Say:**
"I want to make one argument today, and get one decision out of you. The argument is
that the way we've been recording evidence — fifteen different ways, mostly by accident —
is about to become the thing that breaks us, because of AI. The decision I want is: do
we agree to consolidate on a single, shared evidence model that every repo imports. That's
it. Everything in between is me trying to convince you."

---

## Slide 2 — The shift is already here

**On screen:**
- We are becoming an AI-driven knowledge base.
- Not "will be." *Are.*
- Extraction, synthesis, triage, drafting — increasingly machine-first, human-second.

**Say:**
"Let's be honest about where we are. A growing share of the statements entering our
graphs were not written by a curator. They were extracted, summarised, or drafted by a
model, and a human — maybe — glanced at them afterward. DisMech is already this. The
deep-research pipelines are this. This is not a slide about the future. It's a slide about
the pull request you merged last week. The question is not whether we go AI-driven. It's
whether our infrastructure is honest about the fact that we already have."

*(Purpose 1: everyone leaves knowing we're AI-driven.)*

---

## Slide 3 — The thing AI quietly broke: trust

**On screen:**
- Human era: **the curator *was* the evidence.**
- You trusted the person. Their name was the warrant.
- Machine era: "trust me" is gone. The warrant has to travel *with the statement*.

**Say:**
"Here's the part I really want to land. For twenty years, our evidence model was a
person. When Sabrina asserted a disease–gene link, the evidence was *Sabrina* — her
name, her expertise, her reputation. We didn't write down why, because the who was
enough. That's not sloppiness; it's how human curation worked, and it worked.

A model has no reputation you can lean on. When a machine emits a statement, 'trust me'
is worth nothing — it can be confidently, fluently wrong, and it will be. So the warrant
can no longer live in a person's head. It has to be attached to the statement itself,
mechanically, every time. The uncomfortable consequence: **evidence stops being a nice-to-have
on important claims and becomes mandatory infrastructure on all of them.**"

*(Purpose 2: evidence is now urgent, not optional; trust doesn't scale.)*

---

## Slide 4 — "Evidence" is now two different things

**On screen:**
- Contrary to the human-curation days, **essentially every slot now needs evidence.**
- Sometimes that's **scientific evidence** — a paper, a snippet, a direction of support.
- Sometimes it's a **thin provenance layer** — *which model extracted this statement, from where, how sure.*
- Both are evidence. Both need a home in the schema.

**Say:**
"And 'evidence' now means two quite different things, which is exactly why our schemas
are a mess. Sometimes a claim is a scientific assertion — 'this drug treats this disease'
— and the evidence is a publication, a verbatim snippet, whether it supports or refutes.
That's the classic case.

But most slots aren't like that. Most slots are just… a value a model produced. 'This
label came from GPT-x reading Orphanet.' There's no paper. The evidence *is* the
provenance: which agent, which source, what confidence, was a human in the loop. It's thin,
but it is not optional — it's the difference between a statement we can stand behind and a
hallucination we can't distinguish from one. A real evidence model has to hold *both*
shapes, because in an AI pipeline every single field wants one or the other."

---

## Slide 5 — We have quietly built this fifteen times

**On screen:**

| Repo | "Evidence" looks like |
|---|---|
| **DisMech** | `EvidenceItem{reference, supports, snippet, explanation, evidence_source, images}` |
| **Sieve** | abstract `Evidence` → `Concordance / Literature / ExpertReview / Computational`, `direction`, `evidence_strength`, `eco_code` |
| **koza ingests** (e.g. alliance-genotype) | edge slots: `primary_knowledge_source`, `aggregator_knowledge_source`, `knowledge_level`, `agent_type` |
| **…and ~a dozen more** | phenopacket refs, Mondo provenance, per-ingest one-offs |

**Say:**
"Now the embarrassing slide. Every one of us solved this independently. DisMech has a flat
`EvidenceItem`. Sieve has a whole polymorphic hierarchy with support strength and ECO
codes. Every koza-based ingest — alliance-genotype is my example — stamps a different set
of fields on every edge: knowledge source, knowledge level, agent type. Same idea,
three incompatible spellings, and that's just the three I looked at this morning. Across
Monarch it's easily a dozen-plus. None of them talk to each other. If you wanted to ask
'show me everything a text-mining agent asserted with no human review,' you couldn't —
because that question has a different shape in every repo. We didn't decide to build
fifteen evidence models. We just never decided *not* to."

*(Purpose 3: we've built ~15 redundant models.)*

---

## Slide 6 — Two honest options

**On screen:**
- **Option A — Full, SEPIO-aligned evidence model.** Model the epistemics properly.
- **Option B — A small, shared "evidence" class everyone imports.** The 90% case, shippable.
- Same question underneath: *stop building it fifteen times.*

**Say:**
"So there are two honest ways to fix this, and I want to give both a fair hearing before I
tell you which one I'd pick."

---

## Slide 7 — Option A: the full SEPIO-aligned model

**On screen:**
- **SEPIO** — Scientific Evidence & Provenance Information Ontology (GO-CAM, ClinGen use it).
- Assertion ← evidence line ← evidence item ← source.
- First-class **agents, activities, methods, dates**; evidence *for* evidence; disputes.
- It is a *provenance graph*, not a flat record.
- ✅ Correct, expressive, exactly built for machine-generated chains of reasoning.
- ⚠️ Heavy. Steep to author, steep to adopt, easy to do badly.

**Say:**
"Option A is to do it properly, with SEPIO. SEPIO already models everything I've been
describing: an assertion is backed by evidence lines, evidence lines are made of evidence
items, items point at sources — and crucially every node carries who made it, by what
method, when. It even lets evidence support other evidence, which is *exactly* what a chain
of automated agents is. GO and ClinGen run on this. It is not academic; it is the gold
standard.

The catch is that it's a graph, not a field. It asks every contributor to think like an
epistemologist. If we mandated full SEPIO across fifteen repos tomorrow, we'd get fifteen
subtly-wrong SEPIO implementations and a revolt. It's the right model and the wrong ask —
today."

---

## Slide 8 — Option B: a small shared evidence class

**On screen:**
- One `evidence` microschema. One `EvidenceItem` class. Imported, not re-typed.
- Flat: `reference`, `snippet`, `direction`, `strength`, `evidence_source`, `eco_code` …
- …plus a **provenance profile**: `agent_type`, `knowledge_level`, `knowledge_source`.
- Covers the scientific case *and* the "which model extracted this" case.
- ✅ Shippable this quarter. Adoptable without a PhD. ⚠️ Deliberately less expressive.

**Say:**
"Option B is a small, shared LinkML class — a microschema — that every repo *imports*
instead of hand-rolling. One `EvidenceItem`: a reference, a snippet, a direction of
support, a strength, an ECO code for the scientific case; and the same class also carries
the thin provenance fields — agent type, knowledge level, knowledge source — for the
'a model produced this' case. It's deliberately a slightly degenerate SEPIO: flatter, less
expressive, no full provenance graph. But it fits in your head, it validates in CI, and
you can adopt it in an afternoon."

---

## Slide 9 — My call: B now, built as an on-ramp to A

**On screen:**
- I favour **Option B** — for practical reasons: ship now, adopt everywhere, cover the 90%.
- **But:** in the age of AI, **A is where the puck is going.**
- So B must be a **strict subset / on-ramp to SEPIO**, not a dead end.
- Design rule: every field in B has a clean SEPIO mapping. We grow *into* the graph, never *away* from it.

**Say:**
"Here's my recommendation, and my honest hedge. I favour B. Practically, it's the only one
we can actually get fifteen repos to adopt this year, and it captures the vast majority of
what we record. So: B.

But I don't want to sell it to you as *the* answer, because in an AI-driven world it isn't.
When our pipelines are chains of agents checking other agents, we will *want* evidence for
evidence, provenance graphs, methods as first-class objects — we will want SEPIO. So the
condition I put on Option B is that we build it as a strict subset of SEPIO. Every field
maps cleanly upward. B is the on-ramp, not the destination. We ship the small thing, and we
leave ourselves the ability to grow into the real thing without a rewrite. If we can't
promise that mapping, I'd rather we argue about it now than repaint ourselves into a corner."

---

## Slide 10 — Migration [1/3]: the shape of the fix

**On screen:**
- Author once: `evidence.yaml` → published at `w3id.org/linkml/microschemas/evidence`.
- Everyone else: `imports: [evidence]` and point their `evidence` slot at the shared class.
- Two profiles of one class:
  - **Scientific** → `reference`, `snippet`, `direction`, `eco_code`
  - **Provenance** → `agent_type`, `knowledge_level`, `knowledge_source`
- LinkML already does this. (envar imports the microschema profile by URL — proven.)

**Say:**
"So what does consolidation actually look like? One file. We author the evidence model
once, publish it at a w3id, and every repo imports it — the same way the envar microschema
already imports a shared profile by URL today, so we know LinkML handles this. Nobody
re-types `EvidenceItem` ever again. And the one class has two faces: populate the
scientific fields when you have a paper, populate the provenance fields when you have a
model. Same vocabulary everywhere."

---

## Slide 11 — Migration [2/3]: DisMech, concretely

**On screen:**

*Before (DisMech owns it):*
```yaml
EvidenceItem:
  slots: [reference, reference_title, supports, evidence_source, snippet, explanation, images]
EvidenceItemSupportEnum: [SUPPORT, REFUTE, PARTIAL, NO_EVIDENCE, WRONG_STATEMENT]
```
*After (DisMech imports it):*
```yaml
imports: [linkml:types, evidence]      # ← shared
slots:
  evidence:
    range: EvidenceItem                # ← shared class
    multivalued: true
    inlined_as_list: true
```
- Cost: rename `supports → direction`, `SUPPORT → SUPPORTS` (mechanical, one converter).
- Proven: import resolves, `gen-python` still runs, a real record converts + validates.

**Say:**
"Concretely, DisMech. Today it defines its own `EvidenceItem` and its own support enum.
After: it deletes both and imports the shared model, and its eight evidence-bearing classes
don't even notice — they point at the same `evidence` slot, whose type is now the shared
class. The only real cost is a mechanical rename — `supports` becomes `direction`, `SUPPORT`
becomes `SUPPORTS` — one converter, run once over the data. I've speced this out and the
proof is small and concrete: the import resolves, LinkML still generates DisMech's Python
dataclasses, and one real Antiphospholipid record converts and validates against the shared
class — while the old spelling correctly fails. That's the whole risk surface, and it's
green."

---

## Slide 12 — Migration [3/3]: koza / alliance-genotype-ingest

**On screen:**

Today, `allele.py` stamps every edge:
```python
primary_knowledge_source   = "infores:agrkb"
aggregator_knowledge_source= ["infores:monarchinitiative", "infores:agrkb"]
knowledge_level            = KnowledgeLevelEnum.knowledge_assertion
agent_type                 = AgentTypeEnum.manual_agent      # ← today
```
- That block **is an evidence record.** It's just spelled in Biolink, per-repo.
- Consolidation: those slots become the **provenance profile** of the shared model — defined once, mapped to Biolink.
- The tell: `agent_type = manual_agent` today → `automated_agent` / `text_mining_agent` tomorrow.
- The socket for *"which model extracted this"* is already there. We just need it to mean the same thing everywhere.

**Say:**
"And the koza world, which looks different but isn't. Every alliance-genotype edge already
carries four provenance fields — knowledge source, aggregator, knowledge level, and agent
type. Look at that block: that *is* an evidence record. It's the thin-provenance case from
slide four, already in production, just spelled in Biolink and redefined in every single
ingest.

Consolidation here doesn't mean ripping out Biolink. It means those four slots become the
provenance profile of the *shared* evidence model — defined once, with a mapping to Biolink
— so 'knowledge_level' means the same thing in DisMech, in Sieve, and in forty koza ingests.
And here's the punchline for the whole talk: that field says `agent_type = manual_agent`
today. The day a model writes that edge, it says `automated_agent`. The socket for 'which
machine made this claim, and did a human check' is *already in the data*. We are not
inventing a new requirement. We are admitting we already have one — and agreeing to spell it
the same way."

---

## Slide 13 — The ask

**On screen:**
Do we agree:
1. We are **AI-driven** — already, not eventually.
2. That makes evidence **mandatory infrastructure**, because trust doesn't transfer to machines.
3. We have **~15 redundant evidence models** and it's costing us interoperability.
4. **Consolidating** is worth doing.
5. The mechanism is **one shared `evidence` microschema, imported by every repo** — flat now (Option B), mapped as a strict subset of SEPIO so we can grow into the full model (Option A).

**Say:**
"So the ask. Five things, and I want a nod on each. One: we're AI-driven now. Two: that
makes evidence mandatory, not optional, because we can't inherit a machine's trust. Three:
we've accidentally built this fifteen times. Four: it's worth consolidating. Five: the way
we do it is a single evidence microschema that everyone imports — flat and shippable now,
but built as a strict subset of SEPIO so the day we need the full power, it's a growth, not
a rewrite."

*(Purposes 4 and 5: agree to consolidate; agree the mechanism is a shared imported evidence class.)*

---

## Slide 14 — What I want to walk out with

**On screen:**
- ✅ Agreement in principle to a shared evidence microschema.
- ✅ A volunteer repo #2 after DisMech (koza ingest? Sieve?).
- ✅ Owners for the **B→SEPIO mapping table** — so "on-ramp not dead-end" is real, not a promise.
- Next: I circulate the spec + the DisMech proof-of-concept.

**Say:**
"What I'd love to leave with: agreement in principle, one volunteer repo to be the second
adopter after DisMech so we prove it generalises, and one or two people to own the mapping
from our flat model up to SEPIO — because that mapping is what makes the difference between
'pragmatic first step' and 'fifteenth evidence model.' I'll send round the spec and the
working DisMech proof-of-concept. Thank you — let's argue."

---

### Appendix / backup slides

- **A1 — The B→SEPIO mapping table** (field-by-field: `reference` → evidence item source;
  `agent_type` → SEPIO agent; `knowledge_level` → assertion method; etc.).
- **A2 — Why not just mandate Biolink association slots everywhere?** (They cover provenance,
  not scientific evidence — no snippet, no direction, no ECO. Half the model.)
- **A3 — Governance:** where `evidence.yaml` lives, versioning, who reviews changes.
- **A4 — The `todo.md` case:** pattern-generated statements (DOSDP) as a distinct
  `agent_type` / evidence source — a concrete near-term test of the provenance profile.
