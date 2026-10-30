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
  id, in typed lists), and nothing shared. Rules, policies, agents and resources live
  in a `SieveRegistry` and are referenced by id.
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
