# CLI Reference

SIEVE provides a command-line interface for common operations. All commands are accessed through the `sieve` command.

## Installation

```bash
# Install in development mode
pip install -e .

# Or with uv
uv pip install -e .
```

## Commands Overview

```bash
sieve --help
```

| Command | Description |
|---------|-------------|
| `sieve run` | Launch the web interface |
| `sieve ingest` | Load YAML evidence packets into the database |
| `sieve export` | Export evidence packets to RDF or YAML |
| `sieve validate` | Validate packets against the LinkML schema |

---

## sieve run

Launch the Streamlit web application for interactive curation.

```bash
sieve run
```

This command starts the Streamlit server and opens the web interface in your browser. The application provides:

- Dashboard with curation statistics
- Record browsing and filtering
- Evidence review interface
- Decision making controls
- Export functionality

**Environment Variables:**

| Variable | Description | Default |
|----------|-------------|---------|
| `SIEVE_DEV_MODE` | Enable development mode (bypass auth) | `false` |
| `ORCID_CLIENT_ID` | ORCID OAuth client ID | - |
| `ORCID_CLIENT_SECRET` | ORCID OAuth client secret | - |
| `ORCID_REDIRECT_URI` | OAuth redirect URI | `http://localhost:8501/` |
| `ORCID_SANDBOX` | Use ORCID sandbox | `true` |
| `CURATORS_FILE` | Path to curators.yaml | `curators.yaml` |

---

## sieve ingest

Load YAML evidence packets into the DuckDB database.

```bash
sieve ingest [OPTIONS]
```

**Options:**

| Option | Short | Description | Default |
|--------|-------|-------------|---------|
| `--input-dir` | `-I` | Input directory containing YAML files | `inbox/` |
| `--db` | - | Path to DuckDB database file | `data/curation.duckdb` |

**Examples:**

```bash
# Ingest from default inbox directory
sieve ingest

# Ingest from specific directory
sieve ingest -I /path/to/packets/

# Use custom database path
sieve ingest -I inbox/ --db custom.duckdb
```

**Output:**

```
Ingested 15 new records
Skipped 3 existing records
```

**Behavior:**

- Recursively finds all `.yaml` and `.yml` files in the directory
- Skips records that already exist (based on `id` field)
- Calculates evidence scores automatically
- Reports success, skip, and error counts

---

## sieve export

Export evidence packets to various formats.

```bash
sieve export [OPTIONS]
```

**Options:**

| Option | Short | Description | Default |
|--------|-------|-------------|---------|
| `--input` | `-i` | Input YAML file (single packet) | - |
| `--input-dir` | `-I` | Input directory containing YAML files | - |
| `--output` | `-o` | Output file path | stdout |
| `--output-format` | `-O` | Output format | `rdf` |

**Output Formats:**

| Format | Description | File Extension |
|--------|-------------|----------------|
| `rdf`, `turtle`, `ttl` | RDF Turtle format | `.ttl` |
| `xml`, `rdfxml` | RDF/XML format | `.rdf` |
| `n3` | N3 notation | `.n3` |
| `nt`, `ntriples` | N-Triples | `.nt` |
| `yaml` | YAML (passthrough/combine) | `.yaml` |

**Examples:**

```bash
# Export single file to RDF Turtle
sieve export -i packet.yaml -O rdf -o output.ttl

# Export directory to RDF
sieve export -I exports/accepted/ -O rdf -o accepted.ttl

# Export to RDF/XML
sieve export -i packet.yaml -O xml -o output.rdf

# Export to stdout
sieve export -i packet.yaml -O rdf

# Combine multiple YAML files
sieve export -I packets/ -O yaml -o combined.yaml
```

**RDF Export Behavior:**

The RDF export creates OWL axiom annotations following OBO conventions:

1. **Status Required**: Only packets with status ACCEPTED, REJECTED, or CONTROVERSIAL are exported. Packets without a status or with UNREVIEWED status generate warnings and are skipped.

2. **Status-Specific Properties**:
   - **ACCEPTED**: Adds `oboInOwl:source` with evidence steward ORCID and sources from accepted supporting evidence
   - **REJECTED**: Adds `IAO:0000233` (term tracker item) linking to the evidence packet
   - **CONTROVERSIAL**: Adds `rdfs:comment` with controversy note and `IAO:0000233`

3. **Evidence Sources**: For ACCEPTED packets, evidence items with `direction: SUPPORTS` and `rating: ACCEPTED` contribute additional sources:
   - `publication_id` (from LITERATURE or CONCORDANCE evidence)
   - `source_subject_id` (from CONCORDANCE evidence)
   - `reviewer_orcid` (from EXPERT_REVIEW evidence)

**Example RDF Output:**

```turtle
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix oboInOwl: <http://www.geneontology.org/formats/oboInOwl#> .
@prefix SEPIO: <http://purl.obolibrary.org/obo/SEPIO_> .

_:axiom1 a owl:Axiom ;
    owl:annotatedSource <http://purl.obolibrary.org/obo/MONDO_0004979> ;
    owl:annotatedProperty rdfs:subClassOf ;
    owl:annotatedTarget <http://purl.obolibrary.org/obo/MONDO_0005275> ;
    SEPIO:0000124 <http://purl.org/np/RA9876543210> ;
    oboInOwl:source <https://orcid.org/0000-0002-6601-2165> ;
    oboInOwl:source "PMID:28884740" ;
    oboInOwl:source "ICD10CM:J45" .
```

---

## sieve validate

Validate evidence packets against the LinkML schema.

```bash
sieve validate [OPTIONS]
```

**Options:**

| Option | Short | Description | Default |
|--------|-------|-------------|---------|
| `--input` | `-i` | Input YAML file (single packet) | - |
| `--input-dir` | `-I` | Input directory containing YAML files | - |

**Examples:**

```bash
# Validate a single file
sieve validate -i packet.yaml

# Validate all files in a directory
sieve validate -I inbox/

# Validate exported packets
sieve validate -I exports/accepted/
```

**Output:**

```
ERROR (inbox/bad_packet.yaml): 'assertion' is a required property
WARNING (inbox/packet2.yaml): Unknown field 'extra_field'

Validation Summary:
  Total files:  10
  Valid files:  8
  Total errors: 2
```

**Exit Codes:**

| Code | Meaning |
|------|---------|
| 0 | All files valid |
| 1 | One or more validation errors |

**What is Validated:**

- Required fields present (`id`, `assertion`, `status`)
- Field types match schema (strings, numbers, dates)
- Enum values are valid (CurationStatus, EvidenceType, etc.)
- Numeric constraints (e.g., `0.0 <= evidence_strength <= 1.0`)
- Nested object structure (assertion, evidence items, provenance)

---

## Common Workflows

### Initial Setup

```bash
# Create inbox directory and add evidence packets
mkdir -p inbox/
cp my_packets/*.yaml inbox/

# Validate before ingesting
sieve validate -I inbox/

# Ingest into database
sieve ingest -I inbox/

# Launch web interface for review
sieve run
```

### Export After Curation

```bash
# Export accepted assertions to RDF
sieve export -I exports/accepted/ -O rdf -o accepted_axioms.ttl

# Export all curated packets to combined YAML
sieve export -I exports/ -O yaml -o all_curated.yaml
```

### CI/CD Integration

```bash
# Validate in CI pipeline (exit code indicates success/failure)
sieve validate -I evidence_packets/
if [ $? -ne 0 ]; then
    echo "Validation failed"
    exit 1
fi
```

---

## Troubleshooting

### "No module named 'sieve'"

Ensure the package is installed:
```bash
pip install -e .
# or
uv pip install -e .
```

### "Database file not found"

The database is created automatically on first use. Ensure you have write permissions to the `data/` directory.

### "ORCID authentication failed"

Check that ORCID OAuth credentials are configured:
```bash
export ORCID_CLIENT_ID=your_client_id
export ORCID_CLIENT_SECRET=your_client_secret
```

Or use development mode:
```bash
export SIEVE_DEV_MODE=true
sieve run
```
