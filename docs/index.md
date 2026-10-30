# SIEVE: Scientific Evidence Evaluation & Verification Environment

SIEVE records **why Mondo believes a claim**, and packages that "why" so a curator, or
a machine, can check it. It is an evidence model for ontology claims (subclass
placements, mappings, synonyms, definitions, gene-disease attributes), defined as a
profile of the [SEPIO](https://github.com/sepio-framework/sepio-linkml) core
information model and traced requirement by requirement to the Mondo requirements
collection.

New here? Start with the [Primer](primer.md).

## Key concepts

Everything hangs off one container per claim, the versioned **`EvidencePacket`**:

- **A statement**: the claim, as one of ten claim types (`SubclassStatement`,
  `MappingStatement`, `SynonymStatement`, ...). Subject, predicate and object sit on
  the statement; `negated: true` makes a negative claim.
- **Evidence items**: the information used as evidence (`ExternalRecord`,
  `ConcordantAssertion`, `TextPassage`, `Publication`, `WebPage`,
  `GuidelineDocument`, `ComputationalScore`), in typed lists on the packet.
- **Evidence lines**: each `SieveEvidenceLine` is one judgement that some items
  support or dispute the claim, with a strength in [0, 1] and the
  `InterpretationActivity` that produced it.
- **Assertion decisions**: each `AssertionDecision` records whether the claim was
  accepted, rejected, kept as controversial or deferred, by whom, by which route, and
  on which packet version and inclusion score.

!!! note "Two levels of judgement, three axes"
    Interpreting evidence (lines) and deciding on the claim (decisions) are recorded
    separately. Provenance (where a claim came from), evidence (whether it is
    supported) and data quality (whether the evidence was read correctly) are kept
    apart. The claim type's aggregation rule turns the lines into an **inclusion
    score** S in [-1, 1].

For every field, see the [Data Model](data-model.md). For which requirement each part
answers, see [Requirements Traceability](requirements-traceability.md). The small,
separate kernel for other Monarch projects is described in
[Minimal Evidence Model](monarch-evidence.md).

## Quick start

```bash
uv sync --group dev

# Validate a packet against the profile
uv run linkml-validate -s schema/sieve.yaml -C EvidencePacket my_packet.yaml

# Regenerate the Pydantic model and the traceability page after schema edits
just gen-pydantic
just gen-traceability

# Run the profile, traceability and example tests
uv run pytest tests/test_profile_schema.py tests/test_profile_examples.py \
    tests/test_profile_checks.py tests/test_traceability.py
```

linkml-validate needs dates quoted in YAML (see [Data Model](data-model.md#validation)).
The fixtures in `tests/data/profile/valid/` leave dates unquoted, so the CLI rejects
them as they are; the tests load them with dates kept as strings.

!!! warning "Application layer not yet migrated"
    The review app, the DuckDB store, ingest, RDF export, scoring and the `sieve` CLI
    still target the pre-profile model and do not work with the current schema. They
    are being migrated (`issues/issue_migrate_app_to_profile.md`). The
    [CLI Reference](cli.md), [Workflows](workflows.md) and [Python API](api.md) pages
    mark which parts this affects.

## Use cases

- Evidence-based curation of Mondo claims
- Keeping the origin of a claim apart from the evidence for it
- Mapping and cross-ontology alignment review
- Policy-based and batch acceptance with an audit trail
- Recording AI-extracted evidence with the checks a reviewer needs

## Documentation

- [Primer](primer.md): plain-language introduction to the model
- [Minimal Evidence Model](monarch-evidence.md): the separate reusable microschema
- [Data Model](data-model.md): the profile, module by module
- [Architecture](architecture.md): schema, checks and application components
- [Schema Reference](elements/index.md): generated per-class and per-slot pages
- [Requirements Traceability](requirements-traceability.md): requirement to schema element
- [CLI Reference](cli.md) and [Workflows](workflows.md): commands and recipes
- [Python API](api.md): module and function reference
- [AI Integration](ai-integration.md): authoring packets as an AI agent

## Technology stack

- **Python 3.10+**, `uv`, `just`
- **LinkML** for the schema, validation and the generated Pydantic model
- **DuckDB**, **Streamlit**, **RDFLib** and **Typer** in the (pre-profile) application layer

## Contributing

Issues and pull requests are welcome in the
[GitHub repository](https://github.com/matentzn/sieve).
