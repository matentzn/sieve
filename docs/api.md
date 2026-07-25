# Python API Reference

This document describes the Python modules and functions available in SIEVE for programmatic access.

## Module Overview

| Module | Purpose |
|--------|---------|
| `sieve.models` | Pydantic data models |
| `sieve.db` | Database operations |
| `sieve.ingest` | YAML ingestion |
| `sieve.export` | YAML export |
| `sieve.rdf_export` | RDF generation |
| `sieve.validators` | Schema validation |
| `sieve.auth` | Authentication |

---

## sieve.models

Pydantic models representing the data structures.

### Enumerations

```python
from sieve.models import (
    CurationStatus,
    DecisionType,
    EvidenceType,
    EvidenceDirection,
    SourceType,
)

# CurationStatus values
CurationStatus.UNREVIEWED
CurationStatus.ACCEPTED
CurationStatus.REJECTED
CurationStatus.CONTROVERSIAL

# DecisionType values
DecisionType.ACCEPT
DecisionType.REJECT
DecisionType.CONTROVERSIAL

# EvidenceType values
EvidenceType.CONCORDANCE
EvidenceType.LITERATURE
EvidenceType.EXPERT_REVIEW
EvidenceType.COMPUTATIONAL
EvidenceType.OTHER

# EvidenceDirection values
EvidenceDirection.SUPPORTS
EvidenceDirection.CONTRADICTS
EvidenceDirection.UNCERTAIN
```

### Core Models

```python
from sieve.models import (
    CurationRecord,
    Assertion,
    Evidence,
    AssertionProvenance,
    CurationActivity,
    EvidenceSynthesis,
    CurationDecision,
)

# Create an assertion
assertion = Assertion(
    subject_id="MONDO:0004979",
    subject_label="asthma",
    predicate="rdfs:subClassOf",
    object_id="MONDO:0005275",
    object_label="respiratory system disorder",
)

# Create evidence
evidence = Evidence(
    id="ev-001",
    evidence_type=EvidenceType.LITERATURE,
    direction=EvidenceDirection.SUPPORTS,
    evidence_strength=0.9,
    publication_id="PMID:12345",
    quoted_text="Asthma is a respiratory disease...",
)

# Create a curation record
record = CurationRecord(
    id="http://example.org/record1",
    assertion=assertion,
    evidence=[evidence],
    status=CurationStatus.UNREVIEWED,
)

# Serialize to dict
record_dict = record.model_dump(mode="json", exclude_none=True)
```

---

## sieve.db

Database operations using DuckDB.

### CurationDatabase

```python
from sieve.db import CurationDatabase

# Initialize database (creates file if not exists)
db = CurationDatabase("data/curation.duckdb")

# Insert a record
record_id = db.insert_record(record)

# Get a single record
record = db.get_record("record-id")
# Returns dict with all fields including parsed JSON

# Check if record exists
exists = db.record_exists("record-id")

# Get records by status
unreviewed = db.get_records_by_status("UNREVIEWED")
accepted = db.get_records_by_status("ACCEPTED")

# Get paginated records
records, total = db.get_records_paginated(
    status="UNREVIEWED",
    offset=0,
    limit=50,
    sort_by="evidence_score",
    sort_order="DESC",
)

# Get records with decision info
records, total = db.get_records_with_decisions_paginated(
    status="ACCEPTED",
    offset=0,
    limit=50,
)

# Update record status
db.update_status(
    record_id="record-id",
    status="ACCEPTED",
    evidence_steward="orcid:0000-0001-2345-6789",
    confidence=0.95,
)

# Update evidence rating
db.update_evidence_rating(
    record_id="record-id",
    evidence_index=0,  # First evidence item
    rating="ACCEPTED",
)

# Record a decision
from datetime import datetime
from sieve.models import CurationDecision, DecisionType

decision = CurationDecision(
    id="decision-001",
    record_id="record-id",
    curator_orcid="orcid:0000-0001-2345-6789",
    curator_name="Dr. Smith",
    decision=DecisionType.ACCEPT,
    certainty=0.9,
    rationale="Strong evidence from multiple sources",
    decided_at=datetime.now(),
)
db.record_decision(decision)

# Get decisions for a record
decisions = db.get_decisions_for_record("record-id")

# Return to queue (undo decision)
db.return_to_queue("record-id")

# Get statistics
stats = db.get_stats()
# Returns: {"total": 100, "unreviewed": 50, "accepted": 30, ...}

# Close connection
db.close()
```

### Evidence Score Calculation

```python
from sieve.db import calculate_evidence_score

evidence_list = [
    {"direction": "SUPPORTS", "evidence_strength": 0.9},
    {"direction": "SUPPORTS", "evidence_strength": 0.8},
    {"direction": "CONTRADICTS", "evidence_strength": 0.5},
]

score = calculate_evidence_score(evidence_list)
# Returns Net Evidence Ratio: (0.9 + 0.8 - 0.5) / (0.9 + 0.8 + 0.5) = 0.545
```

---

## sieve.ingest

Functions for loading YAML evidence packets.

```python
from pathlib import Path
from sieve.ingest import (
    parse_curation_record,
    ingest_file,
    ingest_directory,
    load_yaml_file,
    generate_id,
)
from sieve.db import CurationDatabase

# Generate a unique ID
new_id = generate_id()  # e.g., "cura:a1b2c3d4e5f6"

# Load and parse a YAML file
data = load_yaml_file(Path("packet.yaml"))
record = parse_curation_record(data)

# Ingest a single file
db = CurationDatabase("data/curation.duckdb")
success_count, skip_count = ingest_file(Path("packet.yaml"), db)

# Ingest a directory
stats = ingest_directory(Path("inbox/"), db)
# Returns: {
#     "files": 10,
#     "success": 8,
#     "skipped": 2,
#     "errors": 0,
#     "error_details": []
# }
```

---

## sieve.export

Functions for exporting records to YAML.

```python
from pathlib import Path
from sieve.export import (
    record_to_export_dict,
    record_to_yaml,
    generate_export_records,
    create_export_tarball,
    export_records_to_directory,
)
from sieve.db import CurationDatabase

db = CurationDatabase("data/curation.duckdb")

# Convert a database record to export dict
record = db.get_record("record-id")
decisions = db.get_decisions_for_record("record-id")
export_dict = record_to_export_dict(record, decisions[0] if decisions else None)

# Convert to YAML string
yaml_str = record_to_yaml(record, decisions[0] if decisions else None)

# Generate all exportable records
for filename, yaml_content, status in generate_export_records(db):
    print(f"{filename}: {status}")

# Create a tar.gz archive
tarball_bytes = create_export_tarball(db, statuses=["ACCEPTED", "REJECTED"])
with open("export.tar.gz", "wb") as f:
    f.write(tarball_bytes)

# Export to directory structure
counts = export_records_to_directory(
    db,
    output_dir=Path("exports/"),
    statuses=["ACCEPTED", "REJECTED", "CONTROVERSIAL"],
)
# Creates: exports/accepted/*.yaml, exports/rejected/*.yaml, etc.
```

---

## sieve.rdf_export

Functions for generating RDF axiom annotations.

```python
from pathlib import Path
from rdflib import Graph
from sieve.rdf_export import (
    packet_to_rdf,
    load_packet,
    iter_packets,
    export_to_rdf,
    expand_curie,
    get_obo_converter,
)

# Load a single packet
packet = load_packet(Path("packet.yaml"))

# Convert to RDF
graph = Graph()
packet_to_rdf(packet, graph)

# Serialize
turtle_str = graph.serialize(format="turtle")

# Expand CURIEs
converter = get_obo_converter()
uri = expand_curie("MONDO:0004979", converter)
# Returns: URIRef("http://purl.obolibrary.org/obo/MONDO_0004979")

# Iterate over packets in a directory
for file_path, packet_dict in iter_packets(Path("exports/accepted/")):
    print(f"Processing {file_path}")

# Export to file
rdf_str = export_to_rdf(
    input_path=Path("exports/accepted/"),
    output_path=Path("axioms.ttl"),
    format="turtle",
)

# Export to different formats
export_to_rdf(Path("packet.yaml"), Path("output.rdf"), format="xml")
export_to_rdf(Path("packet.yaml"), Path("output.n3"), format="n3")
export_to_rdf(Path("packet.yaml"), Path("output.nt"), format="nt")
```

---

## sieve.validators

Functions for validating evidence packets against the LinkML schema.

```python
from pathlib import Path
from sieve.validators import (
    validate_json_schema,
    validate_packet,
    validate_packets,
    print_validation_report,
    get_schema_path,
)

# Get schema path
schema_path = get_schema_path()

# Validate a dictionary
data = {
    "id": "test-001",
    "status": "UNREVIEWED",
    "assertion": {
        "subject_id": "MONDO:0001",
        "predicate": "rdfs:subClassOf",
        "object_id": "MONDO:0002",
    },
}
report = validate_json_schema(data, target_class="CurationRecord")

# Print validation results
error_count = print_validation_report(report)

# Validate a file
report, error_count = validate_packet(Path("packet.yaml"))

# Validate multiple files
total_files, valid_files, total_errors = validate_packets(
    input_path=Path("inbox/"),
    fail_on_error=True,
)
print(f"Valid: {valid_files}/{total_files}, Errors: {total_errors}")
```

---

## sieve.auth

Authentication and authorization functions.

```python
from sieve.auth import (
    is_dev_mode,
    is_orcid_configured,
    is_authorized_curator,
    is_admin,
    get_curator_role,
    get_curator_info,
    load_authorized_curators,
    get_authorization_url,
    exchange_code_for_token,
    OrcidUser,
    AuthorizedCurator,
)

# Check modes
if is_dev_mode():
    print("Running in development mode")

if is_orcid_configured():
    auth_url = get_authorization_url()
    print(f"Login at: {auth_url}")

# Check authorization
orcid = "0000-0001-2345-6789"
if is_authorized_curator(orcid):
    role = get_curator_role(orcid)  # "admin" or "curator"
    if is_admin(orcid):
        print("User is an admin")

# Load all authorized curators
curators = load_authorized_curators()
for orcid, curator in curators.items():
    print(f"{curator.name}: {curator.role}")

# Exchange OAuth code for token (in OAuth callback)
user = exchange_code_for_token(authorization_code)
if user:
    print(f"Logged in as {user.name} ({user.orcid})")
```

### curators.yaml Format

```yaml
curators:
  - orcid: "0000-0001-2345-6789"
    name: "Dr. Jane Smith"
    role: admin
  - orcid: "0000-0002-3456-7890"
    name: "Dr. John Doe"
    role: curator
```

---

## Usage Examples

### Batch Processing Pipeline

```python
from pathlib import Path
from sieve.db import CurationDatabase
from sieve.ingest import ingest_directory
from sieve.validators import validate_packets
from sieve.rdf_export import export_to_rdf

# Validate input
total, valid, errors = validate_packets(Path("input/"))
if errors > 0:
    raise ValueError(f"Validation failed with {errors} errors")

# Ingest
db = CurationDatabase("data/curation.duckdb")
stats = ingest_directory(Path("input/"), db)
print(f"Ingested {stats['success']} records")

# ... (manual curation in web UI) ...

# Export accepted to RDF
export_to_rdf(
    Path("exports/accepted/"),
    Path("accepted_axioms.ttl"),
    format="turtle",
)
```

### Programmatic Decision Making

```python
from datetime import datetime
from sieve.db import CurationDatabase
from sieve.models import CurationDecision, DecisionType

db = CurationDatabase("data/curation.duckdb")

# Get unreviewed records with high evidence scores
records, total = db.get_records_paginated(
    status="UNREVIEWED",
    sort_by="evidence_score",
    sort_order="DESC",
    limit=100,
)

# Auto-accept records with very high scores
for record in records:
    if record["evidence_score"] > 0.9:
        decision = CurationDecision(
            id=f"auto-{record['id']}",
            record_id=record["id"],
            curator_orcid="orcid:0000-0000-0000-0000",
            curator_name="Automated System",
            decision=DecisionType.ACCEPT,
            certainty=record["evidence_score"],
            rationale="Automatically accepted due to high evidence score",
            decided_at=datetime.now(),
        )
        db.record_decision(decision)
```
