# SIEVE as a SEPIO profile, traced to the Mondo requirements

*Date: 2026-10-29*

## Problem

The Mondo requirements were collected systematically in the SEPIO requirements
workbook (`~/ws/notes/evidence/background/mondo-requirements/
Mondo_Requirements_Collection_Forms.xlsx`, moved there from sepio-linkml on 2026-11-06), with decisions D-001 to D-068 in the
decision log next to it. The SIEVE schema predates them. It is redone from scratch
under two constraints:

1. it is a **profile of the SEPIO core model**: every class specialises a core class,
   and nothing in the core is redefined or widened;
2. every requirement in the workbook maps **traceably** to the schema elements and
   modelling decisions that realise it, grouped by SEPIO design module.

## Decisions

- **Core is the canonical SEPIO core (2026-11-20).** `schema/sepio_core.yaml` is a
  byte-identical copy of `sepio-linkml/src/sepio_linkml/schema/sepio_classes.yaml`
  (commit `47f46b7`), which now has snake_case attributes upstream and declares `type`
  once, as a top-level slot with `designates_type: true` on `Entity`. The profile no
  longer re-declares the type designator per class. The interim generator
  (`scripts/snake_case_core.py`, 2026-11-10) and its `slot_uri` pins are gone, so slot
  IRIs follow the snake_case names (`sepio-model:has_evidence_lines`).
  `tests/test_profile_schema.py` compares the copy with the canonical file when
  sepio-linkml is checked out next to sieve. The core stays a separate file, so the
  profile keeps importing it as a module.
- **snake_case slots, CamelCase classes (2026-11-10).** Every slot in the core and the
  profile is snake_case; class and enum names keep CamelCase; enum values are
  unchanged. Agreed with the SEPIO maintainers, and done upstream in sepio-linkml. This
  replaces the earlier camelCase decision (2026-10-29) and matches `minimal.yaml`,
  which was already snake_case.
- **Codegen workarounds, not core patches.** The core `Activity.date` (range `date`)
  shadows the type in generated Pydantic code on Python 3.10, so
  `sieve.datamodel.codegen` aliases the type. With `type` a type designator on
  `Entity`, every slot ranged on a core class becomes a union of all subclasses, and
  building those models needs more than Python's default recursion limit; the
  generated module raises it (2026-11-20).
- **SEPIO design modules.** The core names no modules, so six are defined from its
  class groups: `statement` (Statement, Proposition, Qualifier), `evidence-item`
  (InformationEntity, Document, DataItem, DataSet, StudyResult), `evidence-line`
  (EvidenceLine), `provenance` (Activity, Contribution, Agent, Method),
  `record-metadata` (RecordMetadata), `utility` (Coding, Extension, Qualifier).
- **Data shape.** One `EvidencePacket` (is_a DataSet, versioned) per claim. It holds
  one claim-type Statement (view B of D-041), whose lines carry their evidence items
  nested in full, and a frozen `reference_snapshot` of the shared reference data.
- **Self-contained packets (2026-11-03).** A packet MUST be self-contained. Its required
  `reference_snapshot` (a `SieveRegistry`) holds a frozen copy of every registry entry it
  references, as of the packet version; `sieve.profile_checks` fails a packet with any
  registry reference (agents, methods, rules, policies, batches, resources, releases,
  including references between snapshot entries) that does not resolve, with the right
  kind, inside it. The registry stays where reference data is maintained.
- **Evidence nested, copies keep their id (2026-11-20).** Each line carries its items in
  full (`has_evidence_items`); so does direct evidence (`has_evidence`). A prior claim or
  passage nests the record or document it is `reported_in`; an origin event nests its
  `source_item`; a higher-order line nests full copies of the lines it reads. The packet
  has no item lists. An item used in several places is copied into each under the same
  id, and copies with the same id must be identical (`COPY_DIVERGENCE`). The ids keep
  what the by-reference design was for: the scorer recognises one source across copies
  (independence clusters, stacked lines matched to the statement's lines by id), a
  correction cites the same passage (D-052), and items stay individually addressable
  (EIT F5 = YES). Links that would nest a line in itself or repeat a copy that is
  already there stay ids, checked by `DANGLING_REFERENCE`: `supersedes`,
  `LineStatusChange.replacement_line`, `TextPassage.derived_from`,
  `AssertionDecision.evidence_line`. Reference data (agents, methods, rules, policies,
  batches, resources, releases) stays referenced by id into the `reference_snapshot`;
  nesting it too was considered and is not done, because dated trust levels and rule
  parameters would be copied into every activity and line. LinkML constraint: JSON
  Schema generation cannot expand a mixin range, so the nesting slots keep the core
  range `InformationEntity` (expanded through the type designator), and
  `NOT_AN_EVIDENCE_ITEM` restricts them to `EvidenceItem` classes. Cost: packets are
  longer (the SPOAN example carries one record three times), invalidating a line means
  updating every copy of it (open: matentzn/sieve#14), and a polymorphic `anyOf` reports invalid nested items less
  precisely (validate the item against its own class for the reason). Replaces
  "Evidence items by reference, not inlined" (2026-11-03). Annotated example:
  `tests/data/profile/valid/c003_spoan_nested_correction.yaml`.
- **Item types name what an item is, never its role (2026-11-10).** Evidence items are
  typed by form: a structured claim (any claim-type Statement), `TextPassage`, a
  record or document (`ExternalRecord`, `Publication`, `WebPage`, `GuidelineDocument`),
  `ComputationalScore`. A structured prior claim is typed by what it claims: a DOID
  subclass assertion is a `SubclassStatement` asserted by DOID, nested in the line that
  cites it. Whether it supports, disputes or competes is set by that line. `ConcordantAssertion` and `CompetingClaim` are gone. Source type
  (database, publication) is a property of the record or document a claim is
  `reported_in`, not of the claim. The curation slots of a claim (`review_state`,
  `assertion_decisions`, `origin`, `proposing_channel`, `has_evidence_lines`, `score`)
  belong to the packet's own claim only (`PRIOR_CLAIM_CURATION`, `REVIEW_STATE`); predicate
  bindings apply to prior claims as well. See matentzn/sieve#13.
- **Competing claims (D-069, 2026-11-03).** A competitor is a prior claim carrying its
  log-odds from its own evidence (`own_log_odds`, `log_odds_basis`), frozen into the
  packet. All live competitors enter through ONE disputing line whose act has
  `method_type: COMPETING_CLAIM`; weight ln(1 + Σ e^L_j), outside k. Only claim types whose
  AggregationRule is `exclusive` may have one (synonyms, mappings). Profile checks:
  `COMPETING_CLAIM_LINE` (shape, count, exclusivity) and `CONTESTED_AUTO_ACCEPT` (no
  automated acceptance while the line is live).
- **Unknown human interpreter (2026-11-03).** `SieveAgent.identity_known: false` marks a
  person whose identity was not recorded (legacy data). It must be subtype person
  (`UNKNOWN_AGENT`); a sign-off by one is a WARNING (`UNKNOWN_HUMAN_DECISION`); its lines
  get the rule's `default_quality` as prior unless the act snapshots a trust level.
- **Reference inclusion score (`sieve.inclusion_score`, 2026-11-03).** D-063 + D-069,
  every parameter read from the packet's frozen AggregationRule (`claim_priors`,
  `scaling_factor`, `default_quality`, `confidence_floor`, `stacked_lines`, `exclusive`).
  q is the interpreter's trust for judgement lines and the best valid source rating
  otherwise (Q2). Two choices the decision log leaves open are made explicit and
  per-rule: for a line with several items, q is the best-rated source; for a
  higher-order line, `stacked_lines` = CAP_AND_ADD (it counts too, capped at the
  strongest line it rests on, Q5) or REPLACE_INPUTS (it stands for its inputs).
- **Claim types = Statement profiles.** One class per C001–C010, each binding its
  `predicate` to a value set (`bindings`). The claim-evidence matrix is a
  `permitted_evidence` annotation on each class.
- **No Propositions.** SPO and `negated` sit on the Statement. Core `proposition` /
  `target_proposition` are documented as unused.
- **Two levels of judgement.** `SieveEvidenceLine` (immutable, with
  `InterpretationActivity`, validity, supersession) and `AssertionDecision` (outcome,
  route, S, rule, packet version, policy / batch). Automated routes can only accept
  (class rules).
- **Three axes kept apart.** Provenance (`OriginEvent`, `ResolutionChain`,
  contributions), evidence (lines, strength in [0, 1]) and data quality (line /
  step `confidence` + required basis). Statement `score` is the inclusion score S in
  [-1, 1]; `strength` is its band.

## Traceability mechanism

- `requirements/mondo_requirements.tsv`: 104 response rows extracted from the
  workbook by `scripts/extract_requirements.py` (category rows skipped).
- `requirements/traceability.yaml`: per requirement, its module, disposition
  (`modelled`, `negative_constraint`, `not_desired`, `out_of_scope`), decisions and
  rationale.
- Schema elements carry `annotations.requirements` / `annotations.decisions`, so
  element-level mappings live next to the model and cannot drift.
- `tests/test_traceability.py` enforces: TSV ⇔ trace entries; F2 = N ⇔ negative
  disposition; annotated dispositions ⇔ ≥ 1 annotated element; annotated IDs exist;
  module core classes exist; the rendered matrix (`docs/requirements-traceability.md`)
  is current; TSV = workbook (when the workbook is checked out).
- `negative_constraint` covers N answers that are themselves design decisions
  (`EINT.FLAT_COLLAPSE`, `RCS.STRUCTURED_PROPOSITION`).

Result: 80 modelled, 2 negative constraints, 19 not desired, 3 out of scope (the
term-centric and direct-edge forms of CRS, which belong to Mondo's own model and
release pipeline).

## Enforcement

- `linkml-validate` / JSON Schema: ranges, enums, cardinality, class rules (policy and
  provider routes accept only and name their policy; batch decisions name batch and
  review depth; confidence needs a basis).
- `sieve.profile_checks`: everything that reads inside a Coding or across references
  (predicate bindings, claim-evidence matrix, nested item types, copy consistency,
  dangling id links, read coverage,
  methods on AI and rule-based lines, chain contiguity, supersession, blind approvals,
  and the WARNING states of D-011 and D-029). Every issue names its requirement.

## Out of scope / not done

- The application layer (`app.py`, `scoring.py`, `store.py`, loaders, export and
  ingest, CLI, LinkML-Map transforms) still targets the old model and is broken.
- Logical definitions as class expressions (C004 uses one statement per
  `intersection_of` element).
- C009 / C010 predicates use `sieve:` placeholder IRIs.
