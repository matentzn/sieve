# SIEVE: Scientific Evidence Evaluation & Verification Environment

SIEVE records **why we believe an ontology assertion** — and packages that "why"
so a curator, or a machine, can check it. It is a framework for gathering,
evaluating, and exporting the evidence for and against ontological claims (such
as subclass relationships in disease ontologies).

New here? Start with the [Primer](primer.md) for a plain-language tour, then come
back for the quick start below.

## Key concepts

Everything in SIEVE hangs off one container, the **`EvidencePacket`**, which
bundles four things:

- **A statement** — the single claim being judged (`SieveStatement`: a
  subject → predicate → object triple, e.g. *asthma `rdfs:subClassOf`
  respiratory system disorder*).
- **Evidence lines** — each `SieveEvidenceLine` is *one argument* for or against
  the claim, with a `direction_of_evidence_provided` (`supports` / `disputes` /
  `neutral`) and a strength/score.
- **Typed evidence items** — inside each line, `has_evidence_items[]` holds the
  actual content: a paper (`SieveDocument`), another ontology
  (`ConcordanceItem`), a person's note (`AgentContribution`), a computation
  (`ComputationalResult`), and more. You pick the class with a `type:` field.
- **A verdict** — a `status` (`UNREVIEWED` → `ACCEPTED` / `REJECTED` /
  `CONTROVERSIAL`), an optional synthesis, and the steward (`curated_by`) who
  decided.

!!! note "Two levels: lines, then items"
    Evidence is nested. A single *line* of argument can rest on several *items*
    — "three papers and a clinician all agree" is one supporting line built from
    four items. SIEVE combines the lines into a single **Net Evidence Ratio**
    (`sieve.scoring.net_evidence_ratio`), between −1 (all against) and +1 (all
    for). The [Primer](primer.md) walks a worked example.

For the field-by-field schema, see the [Data Model](data-model.md). For the small
shared core that other Monarch projects can reuse, see the
[Minimal Evidence Model](monarch-evidence.md).

## Quick start

```bash
# Install sieve
pip install -e .

# Ingest evidence packets from inbox/
sieve ingest -I inbox/

# Run the web interface
sieve run

# Export accepted assertions to RDF
sieve export -I exports/accepted/ -O rdf -o accepted.ttl

# Validate evidence packets against schema
sieve validate -I inbox/
```

See the [CLI Reference](cli.md) for every command and option.

## Use cases

- Disease ontology curation (Mondo, DOID)
- Cross-ontology alignment validation
- Evidence-based ontology quality assurance
- Collaborative multi-curator review workflows
- AI-assisted evidence aggregation and synthesis

## Documentation

- [Primer](primer.md) — plain-language introduction to the model
- [Minimal Evidence Model](monarch-evidence.md) — the reusable microschema and transforms
- [Data Model](data-model.md) — LinkML schema, classes, and slots
- [Architecture](architecture.md) — system design and components
- [CLI Reference](cli.md) — command-line interface
- [Workflows](workflows.md) — usage patterns and recipes
- [Python API](api.md) — module and function reference

## Technology stack

- **Python 3.10+** with LinkML for data modeling and validation
- **DuckDB** for local storage (`data/sieve.duckdb`)
- **Streamlit** for the web interface
- **RDFLib** for RDF generation
- **Typer** for the CLI

## Contributing

SIEVE is open source and welcomes contributions — issues, pull requests, and
development guidelines live in the
[GitHub repository](https://github.com/matentzn/sieve).
