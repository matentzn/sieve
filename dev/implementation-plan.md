# Curation App — Implementation Plan & Architecture

## Overview

Build a prototype curation application for reviewing ontology assertions with supporting evidence. Curators review evidence and accept or reject assertions. Accepted assertions are exported as RDF.

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

---

## 1. Project Setup

### 1.1 Directory Structure

```
curation-app/
├── pyproject.toml
├── README.md
├── schema/
│   └── curation_model.yaml       # LinkML schema
├── src/
│   └── curation_app/
│       ├── __init__.py
│       ├── models.py             # Pydantic models (generated from LinkML)
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

### 1.2 pyproject.toml

```toml
[project]
name = "curation-app"
version = "0.1.0"
description = "Ontology assertion curation application"
requires-python = ">=3.11"
dependencies = [
    "streamlit>=1.28.0",
    "duckdb>=0.9.0",
    "pydantic>=2.0.0",
    "linkml>=1.6.0",
    "linkml-runtime>=1.6.0",
    "rdflib>=7.0.0",
    "pyyaml>=6.0",
    "watchdog>=3.0.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0.0",
    "black",
    "ruff",
]

[project.scripts]
curation-app = "curation_app.app:main"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

### 1.3 Installation Commands

```bash
# Create project
mkdir curation-app && cd curation-app

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows

# Install dependencies
pip install -e ".[dev]"

# Generate Pydantic models from LinkML (after schema is created)
gen-pydantic schema/curation_model.yaml > src/curation_app/models.py
```

---

## 2. LinkML Schema

Create `schema/curation_model.yaml`:

```yaml
id: https://w3id.org/curation-app
name: curation_app
title: Curation App Data Model
description: Data model for ontology assertion curation

prefixes:
  linkml: https://w3id.org/linkml/
  cura: https://w3id.org/curation-app/
  orcid: https://orcid.org/
  eco: http://purl.obolibrary.org/obo/ECO_
  schema: http://schema.org/

imports:
  - linkml:types

default_range: string
default_prefix: cura


classes:

  CurationRecord:
    description: A candidate assertion with supporting evidence for curation review
    attributes:
      id:
        identifier: true
        range: string
        description: Unique identifier for this record
      
      assertion:
        range: Assertion
        required: true
        inlined: true
      
      provenance:
        range: AssertionProvenance
        inlined: true
      
      evidence_items:
        range: EvidenceItem
        multivalued: true
        inlined_as_list: true
      
      source_artifact_uri:
        range: uri
        description: URI/path to original source (e.g., nanopub IRI)
      
      source_artifact_type:
        range: ArtifactType
      
      status:
        range: CurationStatus
        required: true
        ifabsent: string(PENDING)
      
      created_at:
        range: datetime
      
      updated_at:
        range: datetime


  Assertion:
    description: The statement being curated (typically an ontology axiom)
    attributes:
      subject_id:
        range: uriorcurie
        required: true
      
      subject_label:
        range: string
      
      predicate:
        range: uriorcurie
        required: true
      
      predicate_label:
        range: string
      
      object_id:
        range: uriorcurie
        required: true
      
      object_label:
        range: string


  AssertionProvenance:
    description: Origin and attribution of the assertion
    attributes:
      attributed_to:
        range: uriorcurie
        description: ORCID or identifier of original creator
      
      attributed_to_label:
        range: string
      
      generated_at:
        range: date
      
      source_version:
        range: string
        description: Version identifier of source (e.g., "Mondo 2024-05-01")
      
      source_uri:
        range: uri


  EvidenceItem:
    description: A piece of evidence supporting the assertion
    attributes:
      id:
        identifier: true
        range: string
      
      evidence_type:
        range: EvidenceType
        required: true
      
      eco_code:
        range: uriorcurie
        description: Evidence ontology code
      
      eco_label:
        range: string
      
      description:
        range: string
        description: Human-readable description of this evidence
      
      # Concordance-specific fields
      source_ontology:
        range: string
        description: Name of concordant ontology (e.g., "ICD-10")
      
      source_subject_id:
        range: uriorcurie
      
      source_subject_label:
        range: string
      
      source_object_id:
        range: uriorcurie
      
      source_object_label:
        range: string
      
      mapping_set_uri:
        range: uri
        description: SSSOM mapping set reference
      
      # Literature-specific fields
      publication_id:
        range: uriorcurie
        description: e.g., PMID:123456
      
      publication_title:
        range: string
      
      quoted_text:
        range: string
        description: Verbatim excerpt from publication
      
      quote_location:
        range: string
        description: Section/page reference
      
      # Expert review-specific fields
      reviewer_orcid:
        range: uriorcurie
      
      reviewer_name:
        range: string
      
      reviewer_affiliation:
        range: string
      
      reviewed_at:
        range: date


  CurationDecision:
    description: A curator's decision on a CurationRecord
    attributes:
      id:
        identifier: true
        range: string
      
      record_id:
        range: string
        required: true
        description: Reference to CurationRecord.id
      
      curator_orcid:
        range: uriorcurie
        required: true
      
      curator_name:
        range: string
      
      decision:
        range: DecisionType
        required: true
      
      rationale:
        range: string
        description: Explanation for decision (required for rejections)
      
      decided_at:
        range: datetime
        required: true


enums:

  CurationStatus:
    permissible_values:
      PENDING:
        description: Awaiting review
      ACCEPTED:
        description: Approved by curator
      REJECTED:
        description: Rejected by curator
      DEFERRED:
        description: Postponed for later review

  DecisionType:
    permissible_values:
      ACCEPT:
      REJECT:
      DEFER:

  EvidenceType:
    permissible_values:
      CONCORDANCE:
        description: Cross-ontology agreement
      LITERATURE:
        description: Published literature support
      EXPERT_REVIEW:
        description: Domain expert validation
      COMPUTATIONAL:
        description: Algorithmic/computed evidence
      OTHER:

  ArtifactType:
    permissible_values:
      NANOPUB:
      YAML_FILE:
      JSON_FILE:
```

---

## 3. Database Layer

Create `src/curation_app/db.py`:

```python
"""DuckDB repository for curation records and decisions."""

import duckdb
import json
from datetime import datetime
from pathlib import Path
from typing import Optional
from .models import CurationRecord, CurationDecision, CurationStatus, DecisionType


class CurationDatabase:
    """DuckDB-backed storage for curation data."""
    
    def __init__(self, db_path: str = "data/curation.duckdb"):
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = duckdb.connect(db_path)
        self._init_schema()
    
    def _init_schema(self):
        """Create tables if they don't exist."""
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS curation_records (
                id VARCHAR PRIMARY KEY,
                assertion_subject_id VARCHAR NOT NULL,
                assertion_subject_label VARCHAR,
                assertion_predicate VARCHAR NOT NULL,
                assertion_predicate_label VARCHAR,
                assertion_object_id VARCHAR NOT NULL,
                assertion_object_label VARCHAR,
                provenance_attributed_to VARCHAR,
                provenance_attributed_to_label VARCHAR,
                provenance_generated_at DATE,
                provenance_source_version VARCHAR,
                provenance_source_uri VARCHAR,
                evidence_items JSON,
                source_artifact_uri VARCHAR,
                source_artifact_type VARCHAR,
                status VARCHAR NOT NULL DEFAULT 'PENDING',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS curation_decisions (
                id VARCHAR PRIMARY KEY,
                record_id VARCHAR NOT NULL,
                curator_orcid VARCHAR NOT NULL,
                curator_name VARCHAR,
                decision VARCHAR NOT NULL,
                rationale TEXT,
                decided_at TIMESTAMP NOT NULL,
                FOREIGN KEY (record_id) REFERENCES curation_records(id)
            )
        """)
    
    def insert_record(self, record: CurationRecord) -> str:
        """Insert a new curation record."""
        evidence_json = json.dumps(
            [e.model_dump(mode='json', exclude_none=True) for e in (record.evidence_items or [])]
        )
        
        self.conn.execute("""
            INSERT INTO curation_records (
                id, assertion_subject_id, assertion_subject_label,
                assertion_predicate, assertion_predicate_label,
                assertion_object_id, assertion_object_label,
                provenance_attributed_to, provenance_attributed_to_label,
                provenance_generated_at, provenance_source_version, provenance_source_uri,
                evidence_items, source_artifact_uri, source_artifact_type,
                status, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [
            record.id,
            record.assertion.subject_id,
            record.assertion.subject_label,
            record.assertion.predicate,
            record.assertion.predicate_label,
            record.assertion.object_id,
            record.assertion.object_label,
            record.provenance.attributed_to if record.provenance else None,
            record.provenance.attributed_to_label if record.provenance else None,
            record.provenance.generated_at if record.provenance else None,
            record.provenance.source_version if record.provenance else None,
            record.provenance.source_uri if record.provenance else None,
            evidence_json,
            record.source_artifact_uri,
            record.source_artifact_type,
            record.status or "PENDING",
            record.created_at or datetime.now(),
            record.updated_at or datetime.now()
        ])
        return record.id
    
    def get_record(self, record_id: str) -> Optional[dict]:
        """Get a single record by ID."""
        result = self.conn.execute(
            "SELECT * FROM curation_records WHERE id = ?", [record_id]
        ).fetchone()
        if result:
            return self._row_to_dict(result)
        return None
    
    def get_records_by_status(self, status: str) -> list[dict]:
        """Get all records with given status."""
        results = self.conn.execute(
            "SELECT * FROM curation_records WHERE status = ? ORDER BY created_at DESC",
            [status]
        ).fetchall()
        return [self._row_to_dict(r) for r in results]
    
    def get_all_records(self) -> list[dict]:
        """Get all records."""
        results = self.conn.execute(
            "SELECT * FROM curation_records ORDER BY created_at DESC"
        ).fetchall()
        return [self._row_to_dict(r) for r in results]
    
    def update_status(self, record_id: str, status: str):
        """Update record status."""
        self.conn.execute(
            "UPDATE curation_records SET status = ?, updated_at = ? WHERE id = ?",
            [status, datetime.now(), record_id]
        )
    
    def record_decision(self, decision: CurationDecision):
        """Record a curation decision and update record status."""
        self.conn.execute("""
            INSERT INTO curation_decisions (
                id, record_id, curator_orcid, curator_name,
                decision, rationale, decided_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, [
            decision.id,
            decision.record_id,
            decision.curator_orcid,
            decision.curator_name,
            decision.decision,
            decision.rationale,
            decision.decided_at
        ])
        
        # Map decision type to status
        status_map = {
            "ACCEPT": "ACCEPTED",
            "REJECT": "REJECTED",
            "DEFER": "DEFERRED"
        }
        self.update_status(decision.record_id, status_map[decision.decision])
    
    def get_decisions_for_record(self, record_id: str) -> list[dict]:
        """Get all decisions for a record."""
        results = self.conn.execute(
            "SELECT * FROM curation_decisions WHERE record_id = ? ORDER BY decided_at DESC",
            [record_id]
        ).fetchall()
        columns = ['id', 'record_id', 'curator_orcid', 'curator_name', 'decision', 'rationale', 'decided_at']
        return [dict(zip(columns, r)) for r in results]
    
    def get_stats(self) -> dict:
        """Get summary statistics."""
        result = self.conn.execute("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN status = 'PENDING' THEN 1 ELSE 0 END) as pending,
                SUM(CASE WHEN status = 'ACCEPTED' THEN 1 ELSE 0 END) as accepted,
                SUM(CASE WHEN status = 'REJECTED' THEN 1 ELSE 0 END) as rejected,
                SUM(CASE WHEN status = 'DEFERRED' THEN 1 ELSE 0 END) as deferred
            FROM curation_records
        """).fetchone()
        return {
            'total': result[0],
            'pending': result[1],
            'accepted': result[2],
            'rejected': result[3],
            'deferred': result[4]
        }
    
    def _row_to_dict(self, row) -> dict:
        """Convert database row to dictionary."""
        columns = [
            'id', 'assertion_subject_id', 'assertion_subject_label',
            'assertion_predicate', 'assertion_predicate_label',
            'assertion_object_id', 'assertion_object_label',
            'provenance_attributed_to', 'provenance_attributed_to_label',
            'provenance_generated_at', 'provenance_source_version', 'provenance_source_uri',
            'evidence_items', 'source_artifact_uri', 'source_artifact_type',
            'status', 'created_at', 'updated_at'
        ]
        d = dict(zip(columns, row))
        # Parse JSON evidence
        if d['evidence_items']:
            d['evidence_items'] = json.loads(d['evidence_items'])
        return d
    
    def record_exists(self, record_id: str) -> bool:
        """Check if a record with given ID exists."""
        result = self.conn.execute(
            "SELECT 1 FROM curation_records WHERE id = ?", [record_id]
        ).fetchone()
        return result is not None
    
    def close(self):
        """Close database connection."""
        self.conn.close()
```

---

## 4. Ingestion Module

Create `src/curation_app/ingest.py`:

```python
"""Ingest YAML files into the curation database."""

import yaml
from pathlib import Path
from datetime import datetime
from typing import Iterator
from uuid import uuid4

from .models import (
    CurationRecord, Assertion, AssertionProvenance, 
    EvidenceItem, CurationStatus
)
from .db import CurationDatabase


def generate_id() -> str:
    """Generate a unique record ID."""
    return f"cura:{uuid4().hex[:12]}"


def load_yaml_file(path: Path) -> dict:
    """Load a YAML file."""
    with open(path, 'r') as f:
        return yaml.safe_load(f)


def parse_curation_record(data: dict) -> CurationRecord:
    """Parse a dictionary into a CurationRecord."""
    
    # Parse assertion
    assertion_data = data.get('assertion', {})
    assertion = Assertion(
        subject_id=assertion_data.get('subject_id'),
        subject_label=assertion_data.get('subject_label'),
        predicate=assertion_data.get('predicate'),
        predicate_label=assertion_data.get('predicate_label'),
        object_id=assertion_data.get('object_id'),
        object_label=assertion_data.get('object_label')
    )
    
    # Parse provenance
    provenance = None
    if 'provenance' in data:
        prov_data = data['provenance']
        provenance = AssertionProvenance(
            attributed_to=prov_data.get('attributed_to'),
            attributed_to_label=prov_data.get('attributed_to_label'),
            generated_at=prov_data.get('generated_at'),
            source_version=prov_data.get('source_version'),
            source_uri=prov_data.get('source_uri')
        )
    
    # Parse evidence items
    evidence_items = []
    for ev_data in data.get('evidence_items', []):
        evidence_items.append(EvidenceItem(
            id=ev_data.get('id', generate_id()),
            evidence_type=ev_data.get('evidence_type'),
            eco_code=ev_data.get('eco_code'),
            eco_label=ev_data.get('eco_label'),
            description=ev_data.get('description'),
            # Concordance fields
            source_ontology=ev_data.get('source_ontology'),
            source_subject_id=ev_data.get('source_subject_id'),
            source_subject_label=ev_data.get('source_subject_label'),
            source_object_id=ev_data.get('source_object_id'),
            source_object_label=ev_data.get('source_object_label'),
            mapping_set_uri=ev_data.get('mapping_set_uri'),
            # Literature fields
            publication_id=ev_data.get('publication_id'),
            publication_title=ev_data.get('publication_title'),
            quoted_text=ev_data.get('quoted_text'),
            quote_location=ev_data.get('quote_location'),
            # Expert review fields
            reviewer_orcid=ev_data.get('reviewer_orcid'),
            reviewer_name=ev_data.get('reviewer_name'),
            reviewer_affiliation=ev_data.get('reviewer_affiliation'),
            reviewed_at=ev_data.get('reviewed_at')
        ))
    
    return CurationRecord(
        id=data.get('id', generate_id()),
        assertion=assertion,
        provenance=provenance,
        evidence_items=evidence_items,
        source_artifact_uri=data.get('source_artifact_uri'),
        source_artifact_type=data.get('source_artifact_type', 'YAML_FILE'),
        status=data.get('status', 'PENDING'),
        created_at=datetime.now(),
        updated_at=datetime.now()
    )


def ingest_file(path: Path, db: CurationDatabase) -> tuple[int, int]:
    """
    Ingest a YAML file into the database.
    Returns (success_count, skip_count).
    """
    data = load_yaml_file(path)
    
    # Handle single record or list of records
    records = data if isinstance(data, list) else [data]
    
    success = 0
    skipped = 0
    
    for record_data in records:
        record = parse_curation_record(record_data)
        
        # Skip if already exists
        if db.record_exists(record.id):
            skipped += 1
            continue
        
        db.insert_record(record)
        success += 1
    
    return success, skipped


def ingest_directory(inbox_path: Path, db: CurationDatabase) -> dict:
    """
    Ingest all YAML files from a directory.
    Returns summary statistics.
    """
    inbox = Path(inbox_path)
    if not inbox.exists():
        inbox.mkdir(parents=True)
        return {'files': 0, 'success': 0, 'skipped': 0, 'errors': 0}
    
    stats = {'files': 0, 'success': 0, 'skipped': 0, 'errors': 0, 'error_details': []}
    
    for yaml_file in inbox.glob('**/*.yaml'):
        stats['files'] += 1
        try:
            success, skipped = ingest_file(yaml_file, db)
            stats['success'] += success
            stats['skipped'] += skipped
        except Exception as e:
            stats['errors'] += 1
            stats['error_details'].append({'file': str(yaml_file), 'error': str(e)})
    
    for yml_file in inbox.glob('**/*.yml'):
        stats['files'] += 1
        try:
            success, skipped = ingest_file(yml_file, db)
            stats['success'] += success
            stats['skipped'] += skipped
        except Exception as e:
            stats['errors'] += 1
            stats['error_details'].append({'file': str(yml_file), 'error': str(e)})
    
    return stats
```

---

## 5. Export Module

Create `src/curation_app/export.py`:

```python
"""Export accepted assertions to RDF."""

from datetime import datetime
from pathlib import Path
from rdflib import Graph, Namespace, Literal, URIRef, BNode
from rdflib.namespace import RDF, RDFS, XSD, PROV, DCTERMS

from .db import CurationDatabase

# Namespaces
CURA = Namespace("https://w3id.org/curation-app/")
ORCID = Namespace("https://orcid.org/")


def export_accepted_records(
    db: CurationDatabase, 
    output_path: Path,
    format: str = "turtle",
    include_provenance: bool = True
) -> Path:
    """
    Export all accepted records to RDF.
    
    Args:
        db: Database connection
        output_path: Directory for output file
        format: RDF serialization format (turtle, xml, json-ld, n3)
        include_provenance: Whether to include curation provenance
    
    Returns:
        Path to generated file
    """
    g = Graph()
    
    # Bind prefixes
    g.bind("cura", CURA)
    g.bind("prov", PROV)
    g.bind("dcterms", DCTERMS)
    g.bind("orcid", ORCID)
    
    accepted_records = db.get_records_by_status("ACCEPTED")
    
    for record in accepted_records:
        # Create the main assertion triple
        subject = URIRef(expand_curie(record['assertion_subject_id']))
        predicate = URIRef(expand_curie(record['assertion_predicate']))
        obj = URIRef(expand_curie(record['assertion_object_id']))
        
        g.add((subject, predicate, obj))
        
        if include_provenance:
            # Get decision info
            decisions = db.get_decisions_for_record(record['id'])
            if decisions:
                decision = decisions[0]  # Most recent
                
                # Create provenance node
                decision_uri = CURA[f"decision/{record['id']}"]
                g.add((decision_uri, RDF.type, CURA.CurationDecision))
                
                # Link to assertion via reification
                assertion_node = BNode()
                g.add((decision_uri, CURA.approvedAssertion, assertion_node))
                g.add((assertion_node, RDF.subject, subject))
                g.add((assertion_node, RDF.predicate, predicate))
                g.add((assertion_node, RDF.object, obj))
                
                # Add decision metadata
                if decision.get('curator_orcid'):
                    g.add((decision_uri, PROV.wasAttributedTo, 
                           URIRef(expand_curie(decision['curator_orcid']))))
                
                if decision.get('decided_at'):
                    g.add((decision_uri, PROV.generatedAtTime,
                           Literal(decision['decided_at'], datatype=XSD.dateTime)))
                
                # Link to source artifact
                if record.get('source_artifact_uri'):
                    g.add((decision_uri, PROV.wasDerivedFrom,
                           URIRef(record['source_artifact_uri'])))
    
    # Generate output filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    ext_map = {'turtle': 'ttl', 'xml': 'rdf', 'json-ld': 'jsonld', 'n3': 'n3'}
    ext = ext_map.get(format, 'ttl')
    
    output_dir = Path(output_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / f"export_{timestamp}.{ext}"
    
    g.serialize(destination=str(output_file), format=format)
    
    return output_file


def expand_curie(curie: str) -> str:
    """Expand common CURIEs to full URIs."""
    prefix_map = {
        'MONDO': 'http://purl.obolibrary.org/obo/MONDO_',
        'DOID': 'http://purl.obolibrary.org/obo/DOID_',
        'HP': 'http://purl.obolibrary.org/obo/HP_',
        'GO': 'http://purl.obolibrary.org/obo/GO_',
        'CHEBI': 'http://purl.obolibrary.org/obo/CHEBI_',
        'ECO': 'http://purl.obolibrary.org/obo/ECO_',
        'orcid': 'https://orcid.org/',
        'PMID': 'https://pubmed.ncbi.nlm.nih.gov/',
        'rdfs': 'http://www.w3.org/2000/01/rdf-schema#',
        'owl': 'http://www.w3.org/2002/07/owl#',
        'skos': 'http://www.w3.org/2004/02/skos/core#',
    }
    
    if '://' in curie:
        return curie  # Already a URI
    
    if ':' in curie:
        prefix, local = curie.split(':', 1)
        if prefix in prefix_map:
            return prefix_map[prefix] + local
    
    return curie


def export_record_as_rdf(record: dict, db: CurationDatabase) -> str:
    """Export a single record to Turtle string."""
    g = Graph()
    g.bind("cura", CURA)
    g.bind("prov", PROV)
    
    subject = URIRef(expand_curie(record['assertion_subject_id']))
    predicate = URIRef(expand_curie(record['assertion_predicate']))
    obj = URIRef(expand_curie(record['assertion_object_id']))
    
    g.add((subject, predicate, obj))
    
    return g.serialize(format='turtle')
```

---

## 6. Streamlit UI

Create `src/curation_app/app.py`:

```python
"""Streamlit UI for the curation application."""

import streamlit as st
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from .db import CurationDatabase
from .ingest import ingest_directory, ingest_file, parse_curation_record
from .export import export_accepted_records, export_record_as_rdf

# Page config
st.set_page_config(
    page_title="Curation App",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize database
@st.cache_resource
def get_db():
    return CurationDatabase("data/curation.duckdb")

db = get_db()


def main():
    """Main application entry point."""
    
    # Sidebar navigation
    st.sidebar.title("🔬 Curation App")
    
    page = st.sidebar.radio(
        "Navigation",
        ["📋 Review Queue", "✅ Accepted", "❌ Rejected", "📥 Ingest", "📤 Export", "📊 Dashboard"]
    )
    
    # Stats in sidebar
    stats = db.get_stats()
    st.sidebar.markdown("---")
    st.sidebar.markdown("### Statistics")
    col1, col2 = st.sidebar.columns(2)
    col1.metric("Pending", stats['pending'])
    col2.metric("Total", stats['total'])
    col1.metric("Accepted", stats['accepted'])
    col2.metric("Rejected", stats['rejected'])
    
    # Curator info
    st.sidebar.markdown("---")
    curator_orcid = st.sidebar.text_input(
        "Your ORCID",
        value=st.session_state.get('curator_orcid', ''),
        placeholder="0000-0000-0000-0000"
    )
    curator_name = st.sidebar.text_input(
        "Your Name",
        value=st.session_state.get('curator_name', ''),
        placeholder="Dr. Jane Smith"
    )
    st.session_state['curator_orcid'] = curator_orcid
    st.session_state['curator_name'] = curator_name
    
    # Route to page
    if page == "📋 Review Queue":
        render_review_queue()
    elif page == "✅ Accepted":
        render_status_list("ACCEPTED")
    elif page == "❌ Rejected":
        render_status_list("REJECTED")
    elif page == "📥 Ingest":
        render_ingest_page()
    elif page == "📤 Export":
        render_export_page()
    elif page == "📊 Dashboard":
        render_dashboard()


def render_review_queue():
    """Render the review queue page."""
    st.title("📋 Review Queue")
    
    pending_records = db.get_records_by_status("PENDING")
    
    if not pending_records:
        st.info("🎉 No pending records to review! Ingest some files to get started.")
        return
    
    st.write(f"**{len(pending_records)} records pending review**")
    
    # Record selection
    record_options = {
        f"{r['assertion_subject_label'] or r['assertion_subject_id']} → {r['assertion_object_label'] or r['assertion_object_id']}": r['id']
        for r in pending_records
    }
    
    selected_label = st.selectbox(
        "Select a record to review",
        options=list(record_options.keys())
    )
    
    if selected_label:
        record_id = record_options[selected_label]
        record = db.get_record(record_id)
        render_review_panel(record)


def render_review_panel(record: dict):
    """Render the review panel for a single record."""
    
    st.markdown("---")
    
    # Assertion display
    st.subheader("📝 Assertion")
    
    col1, col2, col3 = st.columns([2, 1, 2])
    
    with col1:
        st.markdown(f"### {record['assertion_subject_label'] or 'No label'}")
        st.code(record['assertion_subject_id'], language=None)
    
    with col2:
        st.markdown("### →")
        predicate_label = record.get('assertion_predicate_label') or record['assertion_predicate']
        st.markdown(f"**{predicate_label}**")
    
    with col3:
        st.markdown(f"### {record['assertion_object_label'] or 'No label'}")
        st.code(record['assertion_object_id'], language=None)
    
    # Provenance
    if record.get('provenance_attributed_to'):
        st.markdown("---")
        st.subheader("📜 Provenance")
        prov_cols = st.columns(3)
        with prov_cols[0]:
            st.markdown(f"**Attributed to:** {record.get('provenance_attributed_to_label', record['provenance_attributed_to'])}")
        with prov_cols[1]:
            if record.get('provenance_generated_at'):
                st.markdown(f"**Created:** {record['provenance_generated_at']}")
        with prov_cols[2]:
            if record.get('provenance_source_version'):
                st.markdown(f"**Source:** {record['provenance_source_version']}")
    
    # Evidence
    st.markdown("---")
    st.subheader("🔍 Supporting Evidence")
    
    evidence_items = record.get('evidence_items', [])
    
    if not evidence_items:
        st.warning("No evidence items provided for this assertion.")
    else:
        for i, ev in enumerate(evidence_items):
            render_evidence_item(ev, i)
    
    # Decision section
    st.markdown("---")
    st.subheader("⚖️ Your Decision")
    
    if not st.session_state.get('curator_orcid'):
        st.warning("Please enter your ORCID in the sidebar before making decisions.")
        return
    
    rationale = st.text_area(
        "Rationale (required for rejection)",
        placeholder="Explain your decision..."
    )
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button("✅ Accept", type="primary", use_container_width=True):
            make_decision(record['id'], "ACCEPT", rationale)
            st.rerun()
    
    with col2:
        if st.button("❌ Reject", type="secondary", use_container_width=True):
            if not rationale:
                st.error("Rationale is required for rejection.")
            else:
                make_decision(record['id'], "REJECT", rationale)
                st.rerun()
    
    with col3:
        if st.button("⏸️ Defer", use_container_width=True):
            make_decision(record['id'], "DEFER", rationale)
            st.rerun()
    
    with col4:
        if st.button("⏭️ Skip", use_container_width=True):
            st.rerun()


def render_evidence_item(evidence: dict, index: int):
    """Render a single evidence item."""
    
    ev_type = evidence.get('evidence_type', 'OTHER')
    
    # Icon mapping
    icons = {
        'CONCORDANCE': '🔗',
        'LITERATURE': '📚',
        'EXPERT_REVIEW': '👨‍🔬',
        'COMPUTATIONAL': '🤖',
        'OTHER': '📌'
    }
    icon = icons.get(ev_type, '📌')
    
    with st.expander(f"{icon} **{ev_type}** — {evidence.get('description', 'No description')}", expanded=(index == 0)):
        
        # ECO code
        if evidence.get('eco_code'):
            st.markdown(f"**Evidence type:** `{evidence['eco_code']}` ({evidence.get('eco_label', '')})")
        
        # Type-specific rendering
        if ev_type == 'CONCORDANCE':
            render_concordance_evidence(evidence)
        elif ev_type == 'LITERATURE':
            render_literature_evidence(evidence)
        elif ev_type == 'EXPERT_REVIEW':
            render_expert_review_evidence(evidence)
        else:
            st.json(evidence)


def render_concordance_evidence(evidence: dict):
    """Render concordance evidence with mapping visualization."""
    
    st.markdown(f"**Source ontology:** {evidence.get('source_ontology', 'Unknown')}")
    
    if evidence.get('mapping_set_uri'):
        st.markdown(f"**Mapping set:** [{evidence['mapping_set_uri']}]({evidence['mapping_set_uri']})")
    
    # Visual mapping display
    st.markdown("#### Mapping Chain")
    
    col1, col2, col3 = st.columns([2, 1, 2])
    
    with col1:
        st.markdown("**Subject mapping:**")
        if evidence.get('source_subject_id'):
            st.code(f"→ {evidence['source_subject_label'] or evidence['source_subject_id']}", language=None)
    
    with col2:
        st.markdown("**↓**")
    
    with col3:
        st.markdown("**Object mapping:**")
        if evidence.get('source_object_id'):
            st.code(f"→ {evidence['source_object_label'] or evidence['source_object_id']}", language=None)


def render_literature_evidence(evidence: dict):
    """Render literature evidence with quote."""
    
    if evidence.get('publication_id'):
        pub_id = evidence['publication_id']
        if pub_id.startswith('PMID:'):
            pmid = pub_id.replace('PMID:', '')
            st.markdown(f"**Publication:** [{evidence.get('publication_title', pub_id)}](https://pubmed.ncbi.nlm.nih.gov/{pmid})")
        else:
            st.markdown(f"**Publication:** {evidence.get('publication_title', pub_id)}")
    
    if evidence.get('quoted_text'):
        st.markdown("**Quoted text:**")
        st.info(f""{evidence['quoted_text']}"")
        
        if evidence.get('quote_location'):
            st.caption(f"📍 {evidence['quote_location']}")


def render_expert_review_evidence(evidence: dict):
    """Render expert review evidence."""
    
    reviewer_info = []
    if evidence.get('reviewer_name'):
        reviewer_info.append(evidence['reviewer_name'])
    if evidence.get('reviewer_affiliation'):
        reviewer_info.append(evidence['reviewer_affiliation'])
    
    if reviewer_info:
        st.markdown(f"**Reviewer:** {', '.join(reviewer_info)}")
    
    if evidence.get('reviewer_orcid'):
        orcid = evidence['reviewer_orcid'].replace('orcid:', '')
        st.markdown(f"**ORCID:** [{orcid}](https://orcid.org/{orcid})")
    
    if evidence.get('reviewed_at'):
        st.markdown(f"**Reviewed:** {evidence['reviewed_at']}")


def make_decision(record_id: str, decision: str, rationale: str):
    """Record a curation decision."""
    from .models import CurationDecision
    
    decision_obj = CurationDecision(
        id=f"decision:{uuid4().hex[:12]}",
        record_id=record_id,
        curator_orcid=f"orcid:{st.session_state['curator_orcid']}",
        curator_name=st.session_state.get('curator_name'),
        decision=decision,
        rationale=rationale if rationale else None,
        decided_at=datetime.now()
    )
    
    db.record_decision(decision_obj)
    st.success(f"Decision recorded: {decision}")


def render_status_list(status: str):
    """Render list of records with given status."""
    title_map = {"ACCEPTED": "✅ Accepted", "REJECTED": "❌ Rejected", "DEFERRED": "⏸️ Deferred"}
    st.title(title_map.get(status, status))
    
    records = db.get_records_by_status(status)
    
    if not records:
        st.info(f"No {status.lower()} records.")
        return
    
    st.write(f"**{len(records)} records**")
    
    for record in records:
        with st.expander(
            f"{record['assertion_subject_label'] or record['assertion_subject_id']} → "
            f"{record['assertion_object_label'] or record['assertion_object_id']}"
        ):
            st.code(
                f"{record['assertion_subject_id']} {record['assertion_predicate']} {record['assertion_object_id']}",
                language=None
            )
            
            # Show decision info
            decisions = db.get_decisions_for_record(record['id'])
            if decisions:
                d = decisions[0]
                st.markdown(f"**Decided by:** {d.get('curator_name', d['curator_orcid'])}")
                st.markdown(f"**Date:** {d['decided_at']}")
                if d.get('rationale'):
                    st.markdown(f"**Rationale:** {d['rationale']}")


def render_ingest_page():
    """Render the file ingestion page."""
    st.title("📥 Ingest Records")
    
    tab1, tab2 = st.tabs(["📁 From Directory", "📝 Paste YAML"])
    
    with tab1:
        st.markdown("Ingest YAML files from the `inbox/` directory.")
        
        inbox_path = st.text_input("Inbox path", value="inbox/")
        
        if st.button("🔄 Scan & Ingest", type="primary"):
            with st.spinner("Ingesting files..."):
                stats = ingest_directory(Path(inbox_path), db)
            
            if stats['success'] > 0:
                st.success(f"✅ Ingested {stats['success']} new records")
            if stats['skipped'] > 0:
                st.info(f"⏭️ Skipped {stats['skipped']} existing records")
            if stats['errors'] > 0:
                st.error(f"❌ {stats['errors']} errors")
                for err in stats.get('error_details', []):
                    st.code(f"{err['file']}: {err['error']}")
    
    with tab2:
        st.markdown("Paste a YAML record directly.")
        
        yaml_content = st.text_area(
            "YAML content",
            height=400,
            placeholder="""id: example-001
assertion:
  subject_id: MONDO:0005015
  subject_label: diabetes mellitus
  predicate: rdfs:subClassOf
  object_id: MONDO:0005151
  object_label: endocrine system disorder
evidence_items:
  - evidence_type: LITERATURE
    publication_id: PMID:12345
    quoted_text: "Example supporting text..."
"""
        )
        
        if st.button("📥 Ingest YAML"):
            if yaml_content:
                try:
                    import yaml
                    data = yaml.safe_load(yaml_content)
                    record = parse_curation_record(data)
                    
                    if db.record_exists(record.id):
                        st.warning(f"Record {record.id} already exists.")
                    else:
                        db.insert_record(record)
                        st.success(f"✅ Ingested record: {record.id}")
                except Exception as e:
                    st.error(f"Error: {e}")


def render_export_page():
    """Render the export page."""
    st.title("📤 Export Accepted Records")
    
    stats = db.get_stats()
    st.write(f"**{stats['accepted']} accepted records** ready for export")
    
    if stats['accepted'] == 0:
        st.info("No accepted records to export. Review some records first!")
        return
    
    col1, col2 = st.columns(2)
    
    with col1:
        export_format = st.selectbox(
            "Output format",
            options=["turtle", "xml", "json-ld", "n3"],
            index=0
        )
    
    with col2:
        include_provenance = st.checkbox("Include curation provenance", value=True)
    
    if st.button("📤 Generate Export", type="primary"):
        with st.spinner("Generating RDF export..."):
            output_path = export_accepted_records(
                db,
                Path("data/exports"),
                format=export_format,
                include_provenance=include_provenance
            )
        
        st.success(f"✅ Export saved to: `{output_path}`")
        
        # Show preview
        with open(output_path, 'r') as f:
            content = f.read()
        
        st.markdown("### Preview")
        st.code(content[:2000] + ("..." if len(content) > 2000 else ""), language="turtle")
        
        # Download button
        st.download_button(
            label="⬇️ Download",
            data=content,
            file_name=output_path.name,
            mime="text/turtle"
        )


def render_dashboard():
    """Render the dashboard page."""
    st.title("📊 Dashboard")
    
    stats = db.get_stats()
    
    # Metrics row
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Records", stats['total'])
    col2.metric("Pending", stats['pending'], delta=None)
    col3.metric("Accepted", stats['accepted'])
    col4.metric("Rejected", stats['rejected'])
    
    # Progress
    if stats['total'] > 0:
        reviewed = stats['accepted'] + stats['rejected']
        progress = reviewed / stats['total']
        st.progress(progress, text=f"{reviewed}/{stats['total']} reviewed ({progress*100:.0f}%)")
    
    # Recent activity
    st.markdown("---")
    st.subheader("Recent Records")
    
    records = db.get_all_records()[:10]
    
    for r in records:
        status_emoji = {'PENDING': '⏳', 'ACCEPTED': '✅', 'REJECTED': '❌', 'DEFERRED': '⏸️'}
        emoji = status_emoji.get(r['status'], '❓')
        
        st.markdown(
            f"{emoji} **{r['assertion_subject_label'] or r['assertion_subject_id']}** → "
            f"{r['assertion_object_label'] or r['assertion_object_id']} "
            f"({r['status']})"
        )


if __name__ == "__main__":
    main()


def run():
    """Entry point for the application."""
    main()
```

---

## 7. Example Input Files

### 7.1 Simple Example

Create `inbox/examples/diabetes_subclass.yaml`:

```yaml
id: mondo-diabetes-001
assertion:
  subject_id: MONDO:0005015
  subject_label: diabetes mellitus
  predicate: rdfs:subClassOf
  predicate_label: subClassOf
  object_id: MONDO:0005151
  object_label: endocrine system disorder

provenance:
  attributed_to: orcid:0000-0002-9553-7227
  attributed_to_label: Dr. Alice Chen
  generated_at: "2019-03-22"
  source_version: Mondo 2019-03-22
  source_uri: http://purl.obolibrary.org/obo/mondo/releases/2019-03-22/mondo.owl

evidence_items:
  - id: ev-concordance-icd10
    evidence_type: CONCORDANCE
    eco_code: ECO:0000204
    eco_label: similarity evidence
    description: Cross-ontology concordance with ICD-10
    source_ontology: ICD-10
    source_subject_id: ICD10:E11
    source_subject_label: Type 2 diabetes mellitus
    source_object_id: ICD10:E00-E89
    source_object_label: Endocrine, nutritional and metabolic diseases
    mapping_set_uri: https://w3id.org/sssom/mappings/mondo-icd10.sssom.tsv

  - id: ev-literature-1
    evidence_type: LITERATURE
    eco_code: ECO:0000006
    eco_label: experimental evidence
    description: Published literature evidence
    publication_id: PMID:12345678
    publication_title: Classification of Diabetes as an Endocrine Disorder
    quoted_text: >-
      Diabetes mellitus represents a heterogeneous group of metabolic 
      disorders fundamentally rooted in endocrine dysfunction, specifically 
      involving the pancreatic islet cells and their insulin-producing capacity.
    quote_location: Results, Section 3.2, paragraph 1

  - id: ev-expert-review
    evidence_type: EXPERT_REVIEW
    eco_code: ECO:0000218
    eco_label: manual assertion
    description: Clinical specialist review
    reviewer_orcid: orcid:0000-0002-1234-5678
    reviewer_name: Dr. Jane Smith
    reviewer_affiliation: Massachusetts General Hospital, Endocrinology
    reviewed_at: "2024-03-15"

source_artifact_uri: http://purl.org/np/RA1234567890
source_artifact_type: NANOPUB
```

### 7.2 Minimal Example

Create `inbox/examples/asthma_subclass.yaml`:

```yaml
id: mondo-asthma-001
assertion:
  subject_id: MONDO:0004979
  subject_label: asthma
  predicate: rdfs:subClassOf
  object_id: MONDO:0005275
  object_label: respiratory system disorder

evidence_items:
  - id: ev-lit-1
    evidence_type: LITERATURE
    description: Textbook definition
    publication_id: PMID:99999999
    quoted_text: Asthma is a chronic respiratory condition characterized by inflammation of the airways.
```

---

## 8. Running the Application

### 8.1 Development

```bash
# Activate virtual environment
source .venv/bin/activate

# Run Streamlit
streamlit run src/curation_app/app.py

# Or use the entry point
python -m curation_app.app
```

### 8.2 Docker Deployment

Create `Dockerfile`:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml .
COPY src/ src/
COPY schema/ schema/

RUN pip install --no-cache-dir -e .

EXPOSE 8501

CMD ["streamlit", "run", "src/curation_app/app.py", "--server.port=8501", "--server.address=0.0.0.0"]
```

Create `docker-compose.yml`:

```yaml
version: '3.8'
services:
  app:
    build: .
    ports:
      - "8501:8501"
    volumes:
      - ./data:/app/data
      - ./inbox:/app/inbox
```

Run:

```bash
docker-compose up --build
```

---

## 9. Testing

Create `tests/test_ingest.py`:

```python
import pytest
from pathlib import Path
from curation_app.db import CurationDatabase
from curation_app.ingest import parse_curation_record, ingest_file

@pytest.fixture
def db(tmp_path):
    db_path = tmp_path / "test.duckdb"
    return CurationDatabase(str(db_path))

def test_parse_minimal_record():
    data = {
        'id': 'test-001',
        'assertion': {
            'subject_id': 'MONDO:0001',
            'predicate': 'rdfs:subClassOf',
            'object_id': 'MONDO:0002'
        }
    }
    record = parse_curation_record(data)
    assert record.id == 'test-001'
    assert record.assertion.subject_id == 'MONDO:0001'
    assert record.status == 'PENDING'

def test_insert_and_retrieve(db):
    data = {
        'id': 'test-002',
        'assertion': {
            'subject_id': 'MONDO:0001',
            'predicate': 'rdfs:subClassOf',
            'object_id': 'MONDO:0002'
        }
    }
    record = parse_curation_record(data)
    db.insert_record(record)
    
    retrieved = db.get_record('test-002')
    assert retrieved is not None
    assert retrieved['assertion_subject_id'] == 'MONDO:0001'
```

Run tests:

```bash
pytest tests/ -v
```

---

## 10. Implementation Checklist

### Phase 1: Core Setup
- [ ] Create project structure
- [ ] Set up pyproject.toml with dependencies
- [ ] Create LinkML schema
- [ ] Generate Pydantic models (or write manually)

### Phase 2: Backend
- [ ] Implement DuckDB repository (db.py)
- [ ] Implement YAML ingestion (ingest.py)
- [ ] Implement RDF export (export.py)
- [ ] Write unit tests

### Phase 3: UI
- [ ] Create Streamlit app skeleton
- [ ] Implement review queue page
- [ ] Implement evidence renderers (concordance, literature, expert)
- [ ] Implement decision recording
- [ ] Implement ingest page
- [ ] Implement export page
- [ ] Implement dashboard

### Phase 4: Polish
- [ ] Add error handling throughout
- [ ] Add input validation
- [ ] Style improvements
- [ ] Create example files
- [ ] Write README
- [ ] Docker setup

---

## 11. Future Enhancements (Out of Scope for Prototype)

- Nanopub adapter (transform nanopubs to internal format)
- ORCID OAuth authentication
- Multi-curator workflow (consensus)
- File watching (auto-ingest)
- Label lookup via OLS API
- Batch operations
- Search/filter functionality
