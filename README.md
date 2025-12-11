# SIEVE - Scientific Evidence Evaluation & Verification Environment

Ontology assertion curation application for reviewing assertions with supporting evidence.

## Overview

A prototype curation application for reviewing ontology assertions with supporting evidence. Curators review evidence and accept or reject assertions. Accepted assertions are exported as RDF.

### Core Flow

```
LinkML YAML files → Ingest → Review Queue → Curator Decision → Export RDF
     (input)                      (UI)         (accept/reject)   (output)
```

### Tech Stack

| Component | Technology |
|-----------|------------|
| Schema | LinkML |
| Backend | Python 3.11+ |
| Database | DuckDB |
| UI | Streamlit |
| RDF Export | rdflib |

## Installation

```bash
# Install with uv
uv pip install -e ".[dev]"
```

## Usage

### Running the Application

```bash
# Run the Streamlit app
uv run streamlit run src/curation_app/app.py
```

### Ingesting Data

Place YAML files in the `inbox/` directory and use the Ingest page in the UI to import them.

Example YAML format:

```yaml
id: mondo-diabetes-001
assertion:
  subject_id: MONDO:0005015
  subject_label: diabetes mellitus
  predicate: rdfs:subClassOf
  object_id: MONDO:0005151
  object_label: endocrine system disorder

evidence_items:
  - evidence_type: LITERATURE
    publication_id: PMID:12345678
    quoted_text: "Supporting text from literature..."
```

### Running Tests

```bash
uv run pytest tests/ -v
```

## Project Structure

```
sieve/
├── pyproject.toml
├── README.md
├── schema/
│   └── curation_model.yaml       # LinkML schema
├── src/
│   └── curation_app/
│       ├── __init__.py
│       ├── models.py             # Pydantic models
│       ├── db.py                 # DuckDB repository
│       ├── ingest.py             # YAML file ingestion
│       ├── export.py             # RDF export
│       └── app.py                # Streamlit UI
├── data/
│   ├── curation.duckdb           # Database (created at runtime)
│   └── exports/                  # Exported RDF files
├── inbox/                        # Input YAML files
│   └── examples/                 # Example files for testing
└── tests/
    └── test_ingest.py
```

## Evidence Types

- **CONCORDANCE**: Cross-ontology agreement
- **LITERATURE**: Published literature support
- **EXPERT_REVIEW**: Domain expert validation
- **COMPUTATIONAL**: Algorithmic/computed evidence

## Curation Workflow

1. **Ingest**: Import YAML files containing assertions with evidence
2. **Review**: View assertions in the review queue with supporting evidence
3. **Decide**: Accept, reject, or defer each assertion
4. **Export**: Export accepted assertions as RDF/Turtle

## License

MIT
