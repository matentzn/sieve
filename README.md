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
uv run sieve run           # launch the Streamlit review UI
uv run sieve ingest -I inbox/examples/
uv run sieve validate -I inbox/examples/
uv run sieve export -I inbox/examples/ -O rdf -o accepted.ttl
```

### Data model

sieve uses the SEPIO-aligned **SIEVE** model (canonical in `schema/sieve.yaml`,
`id: https://w3id.org/sieve`). A packet is an `EvidencePacket` bundling a
`SieveStatement` with explicit `EvidenceLine`s, each holding typed evidence items.
See `inbox/examples/asthma_subclass.sepio.yaml` for a complete example and
`SPEC.md` for the full model.

```yaml
id: sieve:pkt_example
status: UNREVIEWED
statement:
  id: stmt_1
  type: SieveStatement
  subject: MONDO:0005015
  predicate: {code: rdfs:subClassOf, label: subClassOf}
  object: MONDO:0005151
hasEvidenceLines:
  - id: line_1
    type: SieveEvidenceLine
    directionOfEvidenceProvided: supports
    scoreOfEvidenceProvided: 0.9
    hasEvidenceItems:
      - id: ev_1
        type: SieveDocument
        pmid: "12345678"
        quote: "Supporting text from literature…"
        rating: ACCEPTED
```

### Running Tests

```bash
just test        # pytest + mypy + ruff
```

## Project Structure

```
sieve/
├── schema/
│   ├── sepio_classes.yaml        # SEPIO base
│   └── sieve.yaml                # canonical SIEVE model (imports SEPIO base)
├── src/sieve/
│   ├── datamodel/                # gen-pydantic models + polymorphic loaders
│   ├── scoring.py                # Net Evidence Ratio over EvidenceLines
│   ├── store.py                  # PacketStore (DuckDB)
│   ├── packet_ingest.py          # YAML → validate → store
│   ├── packet_export.py          # EvidencePacket → RDF / YAML
│   ├── cli.py                    # Typer CLI
│   ├── app.py                    # Streamlit UI
│   └── auth.py                   # ORCID OAuth
├── inbox/examples/               # example packets
└── tests/
```

## Evidence item types

`ConcordanceItem`, `SieveDocument`, `SieveDataItem`, `SieveStudyResult`,
`ComputationalResult`, `AgentContribution` — all SEPIO `InformationEntity`
subclasses, each carrying a steward `rating` and `eco_code` via the
`CuratedEvidence` mixin.

## Curation Workflow

1. **Ingest**: import YAML `EvidencePacket`s
2. **Review**: view a packet's statement and evidence lines in the queue
3. **Decide**: rate individual evidence items; accept / reject / flag the packet
4. **Export**: export accepted packets as RDF `owl:Axiom` annotations

## License

MIT
