# Architecture Overview

This document describes the system architecture of SIEVE, including its components, data flow, and design decisions.

## System Components

```
┌─────────────────────────────────────────────────────────────────┐
│                         SIEVE System                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐        │
│  │     CLI      │   │   Web UI     │   │  Python API  │        │
│  │  (cli.py)    │   │  (app.py)    │   │  (modules)   │        │
│  └──────┬───────┘   └──────┬───────┘   └──────┬───────┘        │
│         │                  │                  │                 │
│         └──────────────────┴──────────────────┘                 │
│                            │                                    │
│  ┌─────────────────────────┴─────────────────────────┐         │
│  │              Core Services Layer                   │         │
│  ├────────────┬────────────┬────────────┬───────────┤         │
│  │  ingest.py │  export.py │ rdf_export │ validators │         │
│  │            │            │    .py     │    .py     │         │
│  └────────────┴────────────┴────────────┴───────────┘         │
│                            │                                    │
│  ┌─────────────────────────┴─────────────────────────┐         │
│  │               Data Layer                           │         │
│  ├─────────────────────────┬─────────────────────────┤         │
│  │       db.py             │       models.py         │         │
│  │   (CurationDatabase)    │   (Pydantic models)     │         │
│  └─────────────────────────┴─────────────────────────┘         │
│                            │                                    │
│  ┌─────────────────────────┴─────────────────────────┐         │
│  │             Storage Layer                          │         │
│  ├─────────────────────────┬─────────────────────────┤         │
│  │     DuckDB Database     │   YAML/RDF Files        │         │
│  │  (data/curation.duckdb) │   (inbox/, exports/)    │         │
│  └─────────────────────────┴─────────────────────────┘         │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Module Descriptions

### Entry Points

#### `cli.py` - Command Line Interface
The Typer-based CLI provides commands for:
- `sieve run` - Launch the Streamlit web interface
- `sieve ingest` - Load YAML evidence packets into the database
- `sieve export` - Export evidence packets to RDF or YAML
- `sieve validate` - Validate packets against the LinkML schema

#### `app.py` - Web Interface
A Streamlit application providing:
- Dashboard with curation statistics
- Record browsing and filtering
- Evidence review interface with rating controls
- Decision making (Accept/Reject/Controversial)
- Export functionality

### Core Services

#### `ingest.py` - Data Ingestion
Parses YAML evidence packets and loads them into the database:
- `parse_curation_record(data)` - Convert dict to CurationRecord
- `ingest_file(path, db)` - Load a single YAML file
- `ingest_directory(path, db)` - Batch load from directory

#### `export.py` - YAML Export
Exports curated records back to YAML format:
- `record_to_export_dict(record)` - Convert DB record to export dict
- `record_to_yaml(record)` - Serialize to YAML string
- `create_export_tarball(db)` - Create tar.gz archive
- `export_records_to_directory(db, path)` - Export to directory structure

#### `rdf_export.py` - RDF Export
Generates OWL axiom annotations from evidence packets:
- `packet_to_rdf(packet)` - Convert packet to RDF graph
- `export_to_rdf(input_path, output_path)` - Batch export to RDF file
- Expands CURIEs to full URIs using the OBO converter
- Creates owl:Axiom annotations with appropriate properties based on status

#### `validators.py` - Schema Validation
Validates evidence packets against the LinkML schema:
- `validate_json_schema(data)` - Validate dict against schema
- `validate_packet(path)` - Validate a YAML file
- `validate_packets(path)` - Validate multiple files

### Data Layer

#### `models.py` - Pydantic Models
Defines the data structures:
- `CurationRecord` - Main evidence packet model
- `Assertion` - The ontological statement being curated
- `Evidence` - Evidence item with type-specific fields
- `CurationDecision` - A curator's decision
- Enums: `CurationStatus`, `EvidenceType`, `EvidenceDirection`, etc.

#### `db.py` - Database Layer
DuckDB-backed repository providing:
- `CurationDatabase` class with CRUD operations
- Evidence score calculation (Net Evidence Ratio)
- Decision recording and status updates
- Pagination and filtering for large datasets

### Authentication

#### `auth.py` - ORCID Authentication
Handles curator authentication:
- ORCID OAuth 2.0 flow (sandbox and production)
- Curator authorization via `curators.yaml`
- Role-based access (admin, curator)
- Development mode bypass

## Data Flow

### Ingestion Flow

```
YAML File -> parse_curation_record() -> CurationRecord -> db.insert_record()
                     │                        │
                     ├── Parse assertion      ├── Calculate evidence_score
                     ├── Parse provenance     ├── Serialize to JSON
                     ├── Parse evidence[]     └── Insert into DuckDB
                     └── Parse status
```

### Review Flow

```
Web UI -> get_record() -> Display evidence -> User rates evidence
                                                    │
                                                    ▼
                                          update_evidence_rating()
                                                    │
                                                    ▼
                               User makes decision -> record_decision()
                                                           │
                                                           ├── Insert decision
                                                           ├── Update status
                                                           └── Set evidence_steward
```

### Export Flow

```
                    ┌────────────────────────────────┐
                    │        Export Request          │
                    └───────────────┬────────────────┘
                                    │
                    ┌───────────────┴────────────────┐
                    │                                │
                    ▼                                ▼
            ┌───────────────┐              ┌─────────────────┐
            │  RDF Export   │              │   YAML Export   │
            │ (rdf_export)  │              │    (export)     │
            └───────┬───────┘              └────────┬────────┘
                    │                               │
                    ▼                               ▼
            ┌───────────────┐              ┌─────────────────┐
            │ OWL Axiom     │              │ Evidence Packet │
            │ Annotations   │              │     YAML        │
            └───────────────┘              └─────────────────┘
```

## Database Schema

### curation_records table

| Column | Type | Description |
|--------|------|-------------|
| id | VARCHAR (PK) | Unique record identifier |
| last_updated | DATE | Last update date |
| assertion_subject_id | VARCHAR | Subject CURIE |
| assertion_predicate | VARCHAR | Predicate CURIE |
| assertion_object_id | VARCHAR | Object CURIE |
| evidence | JSON | Array of evidence items |
| evidence_score | DOUBLE | Calculated Net Evidence Ratio |
| status | VARCHAR | UNREVIEWED/ACCEPTED/REJECTED/CONTROVERSIAL |
| evidence_steward | VARCHAR | ORCID of decision maker |
| confidence | DOUBLE | Steward's confidence (0-1) |

### curation_decisions table

| Column | Type | Description |
|--------|------|-------------|
| id | VARCHAR (PK) | Decision identifier |
| record_id | VARCHAR (FK) | Reference to curation_records |
| curator_orcid | VARCHAR | Curator's ORCID |
| decision | VARCHAR | ACCEPT/REJECT/CONTROVERSIAL |
| certainty | DOUBLE | Decision confidence (0-1) |
| rationale | TEXT | Optional explanation |
| decided_at | TIMESTAMP | When decision was made |

## Evidence Score Calculation

SIEVE calculates a **Net Evidence Ratio (NER)** to summarize evidence:

```
NER = (S+ - S-) / (S+ + S- + S?)
```

Where:
- S+ = Sum of evidence_strength for SUPPORTS items
- S- = Sum of evidence_strength for CONTRADICTS items
- S? = Sum of evidence_strength for UNCERTAIN items

The NER ranges from -1 (all contradicting) to +1 (all supporting).

## RDF Export Format

SIEVE exports evidence packets as OWL axiom annotations following OBO conventions:

```turtle
_:axiom a owl:Axiom ;
    owl:annotatedSource <subject_uri> ;
    owl:annotatedProperty rdfs:subClassOf ;
    owl:annotatedTarget <object_uri> ;
    SEPIO:0000124 <evidence_packet_uri> ;    # has_evidence
    oboInOwl:source <evidence_steward_orcid> .
```

### Status-Specific Properties

| Status | Properties Added |
|--------|------------------|
| ACCEPTED | `oboInOwl:source` with steward ORCID and accepted evidence sources |
| REJECTED | `IAO:0000233` (term tracker item) with reference to packet |
| CONTROVERSIAL | `rdfs:comment` with controversy note, `IAO:0000233` |

## Design Decisions

### Why DuckDB?

- Embedded database requiring no server setup
- Excellent performance for analytical queries
- Native JSON support for storing evidence arrays
- Simple deployment (single file)

### Why LinkML?

- Schema-first approach ensures data consistency
- Generates JSON Schema for validation
- Supports rich ontological annotations
- Standard format for biomedical data modeling

### Why YAML for Evidence Packets?

- Human-readable and editable
- Easy to version control with Git
- Compatible with existing ontology workflows
- Supports complex nested structures

### Why Streamlit?

- Rapid UI development in Python
- Interactive widgets for evidence review
- Built-in session state for authentication
- Easy deployment to Streamlit Cloud
