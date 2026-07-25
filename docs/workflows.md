# Workflows and Usage Patterns

This document describes common workflows and best practices for using SIEVE.

## Overview

SIEVE follows a three-phase workflow:

```
┌─────────────────────────────────────────────────────────────────────┐
│                        SIEVE Workflow                               │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│   Phase 1: PREPARATION        Phase 2: CURATION       Phase 3: EXPORT
│   ┌─────────────────┐        ┌─────────────────┐     ┌─────────────┐
│   │ Generate        │        │ Review in       │     │ Export      │
│   │ Evidence        │───────>│ Web UI          │────>│ Results     │
│   │ Packets         │        │                 │     │             │
│   └─────────────────┘        └─────────────────┘     └─────────────┘
│          │                          │                       │
│          ▼                          ▼                       ▼
│   • YAML files              • Rate evidence         • RDF axioms
│   • Validate schema         • Make decisions        • YAML packages
│   • Ingest to DB            • Add rationale         • Audit trail
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Phase 1: Preparation

### Creating Evidence Packets

Evidence packets can be created manually or generated programmatically from various sources.

#### Manual Creation

Create YAML files following the schema:

```yaml
id: http://example.org/evidence/mondo-0004979-subclass
status: UNREVIEWED

assertion:
  subject_id: MONDO:0004979
  subject_label: asthma
  predicate: rdfs:subClassOf
  object_id: MONDO:0005275
  object_label: respiratory system disorder
  display_text: "asthma subClassOf respiratory system disorder"

evidence:
  - id: ev-001
    evidence_type: LITERATURE
    direction: SUPPORTS
    evidence_strength: 0.9
    publication_id: PMID:12345
    quoted_text: "Asthma is a chronic respiratory disease..."
    explanation: "Directly states asthma is respiratory"
```

#### Programmatic Generation

Generate packets from ontology analysis, mapping tools, or AI systems:

```python
from sieve.models import (
    CurationRecord, Assertion, Evidence,
    EvidenceType, EvidenceDirection, CurationStatus
)
import yaml

# Create from ontology diff
def create_packet_from_axiom(subject, predicate, object, evidence_sources):
    record = CurationRecord(
        id=f"http://example.org/packet/{subject}-{object}",
        status=CurationStatus.UNREVIEWED,
        assertion=Assertion(
            subject_id=subject,
            predicate=predicate,
            object_id=object,
        ),
        evidence=[
            Evidence(
                evidence_type=EvidenceType.CONCORDANCE,
                direction=EvidenceDirection.SUPPORTS,
                **source
            )
            for source in evidence_sources
        ],
    )
    return record.model_dump(mode="json", exclude_none=True)

# Write to YAML
packet = create_packet_from_axiom(
    "MONDO:0004979", "rdfs:subClassOf", "MONDO:0005275",
    [{"source_name": "DOID", "source_subject_id": "DOID:2841"}]
)
with open("inbox/packet.yaml", "w") as f:
    yaml.dump(packet, f, sort_keys=False)
```

### Validating Packets

Always validate before ingesting:

```bash
# Validate all packets in inbox
sieve validate -I inbox/

# Check specific file
sieve validate -i inbox/new_packet.yaml
```

Common validation errors:
- Missing required fields (`assertion`, `status`)
- Invalid enum values (e.g., `status: UNKNOWN`)
- Type mismatches (e.g., `evidence_strength: "high"` instead of `0.9`)

### Ingesting Packets

Load validated packets into the database:

```bash
# Ingest from default inbox/
sieve ingest

# Ingest from specific directory
sieve ingest -I /path/to/packets/

# Use custom database
sieve ingest -I inbox/ --db /custom/path.duckdb
```

The ingestion process:
1. Parses each YAML file
2. Calculates evidence scores
3. Inserts records (skips duplicates by ID)
4. Reports success/skip/error counts

---

## Phase 2: Curation

### Starting the Web Interface

```bash
sieve run
```

This opens a Streamlit application with:
- **Dashboard**: Overview statistics
- **Review Queue**: Unreviewed records
- **Accepted/Rejected/Controversial**: Curated records

### Authentication

SIEVE supports three authentication modes:

1. **ORCID OAuth** (Production): Configure credentials in environment
2. **Manual Entry**: Enter ORCID and name in sidebar
3. **Dev Mode**: Set `SIEVE_DEV_MODE=true` to bypass authentication

Configure authorized curators in `curators.yaml`:

```yaml
curators:
  - orcid: "0000-0001-2345-6789"
    name: "Dr. Jane Smith"
    role: admin  # Can return records to queue
  - orcid: "0000-0002-3456-7890"
    name: "Dr. John Doe"
    role: curator  # Standard curation privileges
```

### Review Process

1. **Select a Record**: Browse the review queue, sorted by evidence score
2. **Examine Evidence**: Review each evidence item
3. **Rate Evidence**: Use the dropdown to rate individual items (ACCEPTED, REJECTED, etc.)
4. **Make Decision**: Accept, Reject, or mark as Controversial
5. **Add Rationale**: Provide explanation (required for rejections)

### Evidence Rating

Rating individual evidence items helps track which sources were considered reliable:

| Rating | Meaning |
|--------|---------|
| ACCEPTED | Evidence is valid and trustworthy |
| REJECTED | Evidence is flawed or not applicable |
| CONTROVERSIAL | Evidence quality is disputed |
| UNREVIEWED | Not yet evaluated |

Rated evidence with `ACCEPTED` + `direction: SUPPORTS` is included in RDF export.

### Decision Making

| Decision | When to Use | Result |
|----------|-------------|--------|
| **Accept** | Strong supporting evidence, no significant contradictions | Record moves to ACCEPTED |
| **Reject** | Evidence contradicts assertion or is insufficient | Record moves to REJECTED |
| **Controversial** | Mixed evidence, needs discussion | Record moves to CONTROVERSIAL |

### Admin Actions

Admins can:
- Return records to queue (undo decisions)
- View all curator decisions
- Export data in various formats

---

## Phase 3: Export

### Exporting to RDF

Generate OWL axiom annotations for ontology integration:

```bash
# Export accepted records
sieve export -I exports/accepted/ -O rdf -o accepted.ttl

# Export all curated records
sieve export -I exports/ -O rdf -o all_curated.ttl
```

The RDF output includes:
- OWL axiom annotation structure
- Evidence packet references (SEPIO:0000124)
- Status-specific properties (oboInOwl:source, IAO:0000233)
- Accepted evidence sources

### Exporting to YAML

Generate portable evidence packages:

```bash
# Combine all packets
sieve export -I exports/accepted/ -O yaml -o accepted_packets.yaml

# Keep directory structure
# (Use Python API for this)
```

### Integrating with Ontology Workflows

The RDF export is designed to integrate with OBO ontology release workflows:

```turtle
# Add to ontology as axiom annotation
<http://purl.obolibrary.org/obo/MONDO_0004979>
    rdfs:subClassOf <http://purl.obolibrary.org/obo/MONDO_0005275> .

_:axiom a owl:Axiom ;
    owl:annotatedSource <http://purl.obolibrary.org/obo/MONDO_0004979> ;
    owl:annotatedProperty rdfs:subClassOf ;
    owl:annotatedTarget <http://purl.obolibrary.org/obo/MONDO_0005275> ;
    SEPIO:0000124 <http://purl.org/np/RA123> ;
    oboInOwl:source <https://orcid.org/0000-0001-2345-6789> .
```

---

## Common Patterns

### Continuous Curation Pipeline

```bash
#!/bin/bash
# Daily curation pipeline

# 1. Generate new evidence packets (external tool)
./generate_evidence.sh > inbox/new_packets/

# 2. Validate
sieve validate -I inbox/new_packets/
if [ $? -ne 0 ]; then
    echo "Validation failed"
    exit 1
fi

# 3. Ingest
sieve ingest -I inbox/new_packets/

# 4. Notify curators
echo "New evidence packets ready for review"
```

### Bulk Processing

```python
from sieve.db import CurationDatabase
from sieve.models import CurationDecision, DecisionType
from datetime import datetime

db = CurationDatabase("data/curation.duckdb")

# Auto-accept high-confidence records
records, _ = db.get_records_paginated(
    status="UNREVIEWED",
    sort_by="evidence_score",
    sort_order="DESC",
)

for record in records:
    if record["evidence_score"] > 0.95:
        decision = CurationDecision(
            id=f"auto-{record['id'][:8]}",
            record_id=record["id"],
            curator_orcid="orcid:0000-0000-0000-0001",
            curator_name="Automated Triage",
            decision=DecisionType.ACCEPT,
            certainty=min(record["evidence_score"], 1.0),
            rationale="Auto-accepted: evidence score > 0.95",
            decided_at=datetime.now(),
        )
        db.record_decision(decision)
```

### Quality Assurance

```bash
# Validate all exported packets
sieve validate -I exports/

# Check RDF validity
rapper -c -i turtle exports/accepted.ttl

# Count exported axioms
grep -c "owl:Axiom" exports/accepted.ttl
```

---

## Best Practices

### Evidence Packet Design

1. **Use Stable IDs**: Prefer URIs (nanopub, DOI) over generated IDs
2. **Include Labels**: Add human-readable labels for all CURIEs
3. **Cite Sources**: Always include publication IDs, SSSOM mappings, etc.
4. **Document Provenance**: Record who created the assertion and when

### Curation Guidelines

1. **Review All Evidence**: Consider each evidence item before deciding
2. **Rate Evidence Items**: Track which sources were considered reliable
3. **Provide Rationale**: Especially for rejections and controversial marks
4. **Be Consistent**: Apply the same standards across similar assertions

### Export and Integration

1. **Validate Before Export**: Always validate packets before RDF generation
2. **Use Version Control**: Track exported files in Git
3. **Document Changes**: Include commit messages explaining curation batches
4. **Test Integration**: Verify RDF imports into target ontology
