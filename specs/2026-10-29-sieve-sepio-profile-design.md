# SIEVE as a SEPIO profile, traced to the Mondo requirements

*Date: 2026-10-29*

## Problem

The Mondo requirements were collected systematically in the SEPIO requirements
workbook (`sepio-linkml/docs/requirements-collection/projects/mondo/
Mondo_Requirements_Collection_Forms.xlsx`), with decisions D-001 to D-068 in the
decision log next to it. The SIEVE schema predates them. It is redone from scratch
under two constraints:

1. it is a **profile of the SEPIO core model**: every class specialises a core class,
   and nothing in the core is redefined or widened;
2. every requirement in the workbook maps **traceably** to the schema elements and
   modelling decisions that realise it, grouped by SEPIO design module.

## Decisions

- **Canonical core, unchanged.** `schema/sepio_core.yaml` is a byte-identical copy of
  `sepio-linkml/src/sepio_linkml/schema/sepio_classes.yaml` (commit `8c2c233`), pinned
  by hash in `tests/test_profile_schema.py`. The old trimmed snake_case copy
  (`sepio_classes.yaml`) is gone.
- **camelCase.** Profile names follow the core's camelCase. This supersedes the
  snake_case flip of `2026-07-31-minimal-microschema-and-sieve-alignment-design.md`
  for the full model. `minimal.yaml` is untouched.
- **Python 3.10 `date` workaround in codegen, not in the core.** The core
  `Activity.date` (range `date`) shadows the type in generated Pydantic code.
  `sieve.datamodel.codegen` aliases the type instead of patching the core.
- **SEPIO design modules.** The core names no modules, so six are defined from its
  class groups: `statement` (Statement, Proposition, Qualifier), `evidence-item`
  (InformationEntity, Document, DataItem, DataSet, StudyResult), `evidence-line`
  (EvidenceLine), `provenance` (Activity, Contribution, Agent, Method),
  `record-metadata` (RecordMetadata), `utility` (Coding, Extension, Qualifier).
- **Data shape.** One `EvidencePacket` (is_a DataSet, versioned) per claim. It holds
  one claim-type Statement (view B of D-041), the evidence items its lines refer to (by
  id, in typed lists), and a frozen `referenceSnapshot` of the shared reference data.
- **Self-contained packets (2026-11-03).** A packet MUST be self-contained. Its required
  `referenceSnapshot` (a `SieveRegistry`) holds a frozen copy of every registry entry it
  references, as of the packet version; `sieve.profile_checks` fails a packet with any
  registry reference (agents, methods, rules, policies, batches, resources, releases,
  including references between snapshot entries) that does not resolve, with the right
  kind, inside it. The registry stays where reference data is maintained.
- **Evidence items by reference, not inlined.** Lines list item ids; each item lives once in
  the packet's typed lists. Reasons: one item backs several lines (M2, D1); the same record
  is origin or evidence depending on where it is referenced (D-030); lines can be items of
  higher-order lines (EINT.STACKING); dependence links (`derivedFrom`, `reportedIn`) need
  addressable items; corrections are new lines citing the same items (D-052); and the
  workbook asks for individual addressability (EIT F5 = YES). LinkML adds a technical
  reason: inlined polymorphic items become a JSON-Schema `anyOf` that hides errors. Cost:
  referential integrity is a profile check, not a schema guarantee. An inlined alternative
  (ids + type designators) is tracked in `issues/issue_inline_evidence_items.md`.
- **Competing claims (D-069, 2026-11-03).** A `CompetingClaim` item freezes a competitor's
  SPO and its log-odds from its own evidence (`competitorLogOdds`, `logOddsBasis`) into the
  packet. All live competitors enter through ONE disputing line whose act has
  `methodType: COMPETING_CLAIM`; weight ln(1 + Σ e^L_j), outside k. Only claim types whose
  AggregationRule is `exclusive` may have one (synonyms, mappings). Profile checks:
  `COMPETING_CLAIM_LINE` (shape, count, exclusivity) and `CONTESTED_AUTO_ACCEPT` (no
  automated acceptance while the line is live).
- **Unknown human interpreter (2026-11-03).** `SieveAgent.identityKnown: false` marks a
  person whose identity was not recorded (legacy data). It must be subtype person
  (`UNKNOWN_AGENT`); a sign-off by one is a WARNING (`UNKNOWN_HUMAN_DECISION`); its lines
  get the rule's `defaultQuality` as prior unless the act snapshots a trust level.
- **Reference inclusion score (`sieve.inclusion_score`, 2026-11-03).** D-063 + D-069,
  every parameter read from the packet's frozen AggregationRule (`claimPriors`,
  `scalingFactor`, `defaultQuality`, `confidenceFloor`, `stackedLines`, `exclusive`).
  q is the interpreter's trust for judgement lines and the best valid source rating
  otherwise (Q2). Two choices the decision log leaves open are made explicit and
  per-rule: for a line with several items, q is the best-rated source; for a
  higher-order line, `stackedLines` = CAP_AND_ADD (it counts too, capped at the
  strongest line it rests on, Q5) or REPLACE_INPUTS (it stands for its inputs).
- **Claim types = Statement profiles.** One class per C001–C010, each binding its
  `predicate` to a value set (`bindings`). The claim-evidence matrix is a
  `permitted_evidence` annotation on each class.
- **No Propositions.** SPO and `negated` sit on the Statement. Core `proposition` /
  `targetProposition` are documented as unused.
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
  (predicate bindings, claim-evidence matrix, dangling references, read coverage,
  methods on AI and rule-based lines, chain contiguity, supersession, blind approvals,
  and the WARNING states of D-011 and D-029). Every issue names its requirement.

## Out of scope / not done

- The application layer (`app.py`, `scoring.py`, `store.py`, loaders, export and
  ingest, CLI, LinkML-Map transforms) still targets the old model and is broken.
- Logical definitions as class expressions (C004 uses one statement per
  `intersection_of` element).
- C009 / C010 predicates use `sieve:` placeholder IRIs.
