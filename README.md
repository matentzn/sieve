# SIEVE - Scientific Evidence Evaluation & Verification Environment

An evidence model for Mondo claims, and a curation application built on it.

## Overview

SIEVE records why Mondo believes a claim: the claim, the evidence for and against it,
who interpreted that evidence and how, and who decided to put the claim into Mondo. The
model is a profile of the [SEPIO](https://github.com/sepio-framework/sepio-linkml) core
information model, traced requirement by requirement to the Mondo requirements
collection.

- `schema/sepio_core.yaml`: the SEPIO core, copied unchanged from sepio-linkml
  (commit `8c2c233`, hash-pinned in the tests).
- `schema/sieve.yaml`: the SIEVE profile (`id: https://w3id.org/sieve`). Every class
  specialises a core class; names are camelCase.

Documentation: <https://matentzn.github.io/sieve> (sources in `docs/`). Design:
`specs/2026-10-29-sieve-sepio-profile-design.md`.

> **Status.** The schema, the generated Pydantic model, the profile checks and the
> traceability tooling work. The application layer (Streamlit app, DuckDB store,
> ingest, RDF export, scoring, the `sieve` CLI and the LinkML-Map transforms) still
> targets the pre-profile model and is broken. Migration is tracked in
> `issues/issue_migrate_app_to_profile.md`.

## Data model

One versioned `EvidencePacket` per claim. The statement is one of ten claim types
(C001–C010: `TermExistenceStatement`, `DefinitionStatement`, `SynonymStatement`,
`SubclassStatement`, `NegativeSubclassStatement`, `MappingStatement`,
`DiseaseAttributeStatement`, `SubsetMembershipStatement`, `MetaclassStatement`,
`ValueSetMembershipStatement`), each binding its predicate to a value set and listing
the evidence it accepts. Evidence lines (`SieveEvidenceLine`, each with its
`InterpretationActivity`) sit on the statement and refer by id to evidence items in
typed lists on the packet (`ExternalRecord`, prior claims typed by claim type, `TextPassage`,
`Publication`, `WebPage`, `GuidelineDocument`, `ComputationalScore`). An
`AssertionDecision` records the outcome, route, inclusion score S in [-1, 1], rule,
policy or batch, and the packet version it was given on. Rules, policies, agents and
information resources live in a `SieveRegistry`.

```yaml
id: sieve:pkt/MONDO_0008608-excl-MONDO_0003847
type: EvidencePacket
version: "2026-10-20"
statement:
  id: sieve:st/MONDO_0008608-excl-MONDO_0003847
  type: NegativeSubclassStatement
  subject: MONDO:0008608              # Down syndrome
  predicate: {code: rdfs:subClassOf}
  object: MONDO:0003847               # hereditary disease
  negated: true
  review_state: VERIFIED
  has_evidence_lines:
    - id: sieve:el/ds-doid-dispute
      type: SieveEvidenceLine
      has_evidence_items: [sieve:ca/doid-14250-isa-630]
      direction_of_evidence_provided: disputes
      score_of_evidence_provided: 0.5
      contributions:
        - id: sieve:act/ds-doid-concordance
          type: InterpretationActivity
          contributor: sieve:agent/concordance-pipeline
          date: "2026-10-20"
          method_type: COMPUTED_CONCORDANCE
          specified_by: [sieve:method/concordance-workflow]
prior_claims:
  - id: sieve:ca/doid-14250-isa-630
    type: SubclassStatement            # a prior claim, typed by what it claims
    subject: DOID:14250
    predicate: {code: rdfs:subClassOf}
    object: DOID:630
    reported_in: [DOID:14250]
    resource: infores:disease-ontology
```

Full examples: `tests/data/profile/valid/` (C003, C005, C006, C007) and the registry in
`tests/data/profile/registry.yaml`.

## Installation

```bash
uv sync --group dev
```

## Usage

```bash
# Validate a packet (quote dates in YAML)
uv run linkml-validate -s schema/sieve.yaml -C EvidencePacket my_packet.yaml

# Profile checks linkml-validate cannot express (predicate bindings, claim-evidence matrix, ...)
uv run python -c "import yaml, sys; from sieve.profile_checks import check_packet; print(check_packet(yaml.safe_load(open(sys.argv[1]))))" my_packet.yaml

# After schema or traceability edits
just gen-pydantic          # regenerate src/sieve/datamodel/sieve_models.py
just gen-traceability      # regenerate docs/requirements-traceability.md
just extract-requirements  # re-extract requirements/mondo_requirements.tsv from the workbook

# Tests
just test
```

`just test` currently also runs the legacy application tests, which fail until the
migration lands.

## Requirements traceability

Each schema element that realises a Mondo requirement carries the requirement ID in
`annotations.requirements` (and decision-log IDs in `annotations.decisions`).
`requirements/traceability.yaml` assigns every requirement to a SEPIO design module
(statement, evidence-item, evidence-line, provenance, record-metadata, utility) and a
disposition. `tests/test_traceability.py` keeps the two consistent, and
`docs/requirements-traceability.md` is the generated matrix.

## Project Structure

```
sieve/
├── schema/
│   ├── sepio_core.yaml           # SEPIO core, unchanged
│   ├── sieve.yaml                # SIEVE profile (imports sepio_core)
│   └── minimal.yaml              # minimal evidence microschema (standalone, not connected to the profile)
├── requirements/                 # Mondo requirements TSV + traceability.yaml
├── scripts/                      # extract_requirements.py, render_traceability.py
├── specs/                        # design specs
├── transform/                    # linkml-map: dismech → minimal → sieve (second hop pre-profile)
├── monarch_evidence/             # Monarch evidence modelling: SPEC + corpus + analysis
├── src/sieve/
│   ├── datamodel/                # generated Pydantic models + codegen (loaders.py is pre-profile)
│   ├── profile_checks.py         # profile constraints beyond linkml-validate
│   ├── traceability.py           # requirement ↔ schema element index and matrix
│   ├── scoring.py, store.py, packet_ingest.py, packet_export.py,
│   ├── cli.py, app.py            # application layer (pre-profile, being migrated)
│   └── auth.py                   # ORCID OAuth
├── docs/
└── tests/
    └── data/profile/             # profile example packets and registry
```

## Monarch evidence modelling

`monarch_evidence/` holds the design work behind the evidence schemas: a
[specification](monarch_evidence/SPEC.md), a
[corpus](monarch_evidence/examples/README.md) of real records from DisMech, MeDIC and
mondo-ai, and an [analysis](monarch_evidence/analysis/requirements-matrix.md) of which
requirements are met where. How the minimal microschema relates to the new profile is
open (`issues/issue_minimal_kernel_vs_profile.md`).

## License

Apache-2.0
