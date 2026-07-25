# SIEVE: Scientific Evidence Evaluation & Verification Environment

SIEVE is a framework for curating and managing evidence supporting ontology assertions. It provides a structured approach to collecting, evaluating, and exporting evidence that supports or contradicts ontological axioms (such as subclass relationships in disease ontologies).

## Purpose

SIEVE addresses the need for transparent, traceable evidence management in ontology curation by:

1. **Aggregating Evidence**: Collecting multiple types of evidence (literature, cross-ontology concordance, expert review, computational) for ontological assertions
2. **Enabling Review**: Providing a web interface for knowledge stewards to evaluate and rate evidence
3. **Tracking Provenance**: Recording who made decisions, when, and with what confidence
4. **Exporting Results**: Generating RDF axiom annotations and YAML packages for integration with ontology workflows

## Key Concepts

### Evidence Packets

An **evidence packet** is the core data structure in SIEVE. It bundles:

- An **assertion** (e.g., "asthma subClassOf respiratory system disorder")
- Multiple **evidence items** supporting or contradicting the assertion
- **Provenance** information about the assertion's origin
- **Status** (UNREVIEWED, ACCEPTED, REJECTED, CONTROVERSIAL)
- **Evidence steward** who made the final decision

### Evidence Types

SIEVE supports four primary evidence types:

| Type | Description | Key Fields |
|------|-------------|------------|
| CONCORDANCE | Cross-ontology agreement | `source`, `source_subject_id`, `mapping_set` |
| LITERATURE | Published literature | `publication_id`, `quoted_text`, `explanation` |
| EXPERT_REVIEW | Domain expert validation | `reviewer_orcid`, `reviewer_name`, `reviewed_at` |
| COMPUTATIONAL | Algorithmic evidence | `method`, `confidence_score`, `parameters` |

### Evidence Direction

Each evidence item has a direction indicating whether it:

- **SUPPORTS** - Corroborates the assertion
- **CONTRADICTS** - Provides counter-evidence
- **UNCERTAIN** - Neutral or inconclusive

### Curation Workflow

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   INGEST    │ -> │   REVIEW    │ -> │   EXPORT    │
│  YAML files │    │  Web UI     │    │  RDF/YAML   │
└─────────────┘    └─────────────┘    └─────────────┘
```

1. **Ingest**: Load YAML evidence packets into the database
2. **Review**: Knowledge stewards evaluate evidence and make decisions
3. **Export**: Generate RDF axiom annotations or YAML packages

## Quick Start

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

## Documentation

- [Architecture Overview](architecture.md) - System design and components
- [Data Model](data-model.md) - LinkML schema and data structures
- [CLI Reference](cli.md) - Command-line interface documentation
- [Python API](api.md) - Module and function reference
- [Workflows](workflows.md) - Usage patterns and recipes
- [AI Integration Guide](ai-integration.md) - Information for AI agents working with SIEVE

## Technology Stack

- **Python 3.10+** with Pydantic models
- **LinkML** for data modeling and validation
- **DuckDB** for local storage
- **Streamlit** for web interface
- **RDFLib** for RDF generation
- **Typer** for CLI

## License

This project is open source. See the repository for license details.
