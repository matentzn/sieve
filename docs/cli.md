# CLI Reference

!!! warning "The `sieve` CLI targets the pre-profile model"
    `sieve run`, `ingest`, `export` and `validate` still target the pre-profile model.
    `ingest`, `export` and `validate` fail at import against the current schema. They
    are being migrated (`issues/issue_migrate_app_to_profile.md`). Until then, validate
    packets with `linkml-validate` and `sieve.profile_checks`, and maintain the
    generated artefacts with the `just` recipes below.

## Installation

```bash
uv sync --group dev
```

## Working commands

| Command | What it does |
|---------|--------------|
| `uv run linkml-validate -s schema/sieve.yaml -C EvidencePacket <file>` | Validate a packet against the profile (structure, enums, ranges, class rules) |
| `uv run linkml-validate -s schema/sieve.yaml -C SieveRegistry <file>` | Validate a registry of resources, agents, rules and policies |
| `just gen-pydantic` | Regenerate `src/sieve/datamodel/sieve_models.py` from the schema |
| `just gen-traceability` | Regenerate `docs/requirements-traceability.md` |
| `just extract-requirements [workbook]` | Re-extract `requirements/mondo_requirements.tsv` from the Mondo requirements workbook |
| `just gen-docs` | Regenerate the schema reference in `docs/elements/` |
| `just serve-docs` | Regenerate the schema reference and serve the docs locally |

### linkml-validate

```bash
uv run linkml-validate -s schema/sieve.yaml -C EvidencePacket packet.yaml
```

Prints `No issues found` or one `[ERROR]` line per problem, and exits 1 on errors.
It checks required fields, ranges, enums (`Direction`, `ReviewState`,
`AssertionRoute`, ...), numeric bounds (line `score_of_evidence_provided` in [0, 1],
inclusion score in [-1, 1]) and the class rules (policy and provider routes only
accept and name their policy; batch decisions name batch and review depth; a
confidence needs a basis). The validator is closed, so unknown fields are errors.

Quote dates in YAML (`date: "2026-10-20"`). Unquoted dates are parsed into date
objects and rejected as "not of type 'string'". Predicate bindings and the
claim-evidence matrix are not checked here; run `sieve.profile_checks.check_packet`
for those (see [Workflows](workflows.md#2-validate)).

### just extract-requirements

```bash
just extract-requirements                                   # ../../notes/evidence/background/mondo-requirements/...
just extract-requirements /path/to/Mondo_Requirements_Collection_Forms.xlsx
```

Writes one row per requirement (category rows skipped) to
`requirements/mondo_requirements.tsv`. `tests/test_traceability.py` compares the TSV
with the workbook when the workbook is checked out.

---

## Pre-profile commands

The rest of this page describes the `sieve` commands as implemented.

```bash
uv run sieve --help
```

| Command | Description |
|---------|-------------|
| `sieve run` | Launch the Streamlit web interface |
| `sieve ingest` | Load YAML evidence packets into the database |
| `sieve export` | Export evidence packets to RDF or YAML |
| `sieve validate` | Validate packets against the LinkML schema |

### sieve run

Starts the Streamlit app (dashboard, review queue, ingest and export views).

| Variable | Description | Default |
|----------|-------------|---------|
| `SIEVE_DEV_MODE` | Enable development mode (bypass auth) | `false` |
| `ORCID_CLIENT_ID` | ORCID OAuth client ID | - |
| `ORCID_CLIENT_SECRET` | ORCID OAuth client secret | - |
| `ORCID_REDIRECT_URI` | OAuth redirect URI | `http://localhost:8501/` |
| `ORCID_SANDBOX` | Use ORCID sandbox | `true` |
| `CURATORS_FILE` | Path to curators.yaml | `curators.yaml` |

### sieve ingest

```bash
sieve ingest [-I <dir>] [--db <path>]
```

| Option | Short | Description | Default |
|--------|-------|-------------|---------|
| `--input-dir` | `-I` | Input directory containing YAML files | `inbox/` |
| `--db` | - | Path to DuckDB database file | `data/sieve.duckdb` |

Recursively finds `.yaml` / `.yml` files, validates and upserts each packet into
DuckDB, computes the Net Evidence Ratio, and reports `Ingested N of M packets`.

### sieve export

```bash
sieve export (-i <file> | -I <dir>) [-o <out>] [-O <format>]
```

| Option | Short | Description | Default |
|--------|-------|-------------|---------|
| `--input` | `-i` | Input YAML file (single packet) | - |
| `--input-dir` | `-I` | Input directory containing YAML files | - |
| `--output` | `-o` | Output file path | stdout |
| `--output-format` | `-O` | Output format | `rdf` |

| Format | Description |
|--------|-------------|
| `rdf`, `turtle`, `ttl` | RDF Turtle |
| `xml`, `rdfxml` | RDF/XML |
| `n3` | N3 |
| `nt`, `ntriples` | N-Triples |
| `yaml` | YAML (combine) |

RDF export writes an `owl:Axiom` annotation per decided packet:

- only packets with status `ACCEPTED`, `REJECTED` or `CONTROVERSIAL` are exported;
  others are skipped with a warning;
- `ACCEPTED` adds `oboInOwl:source` for the steward ORCID and for accepted items on
  supporting lines;
- `REJECTED` adds `IAO:0000233` (term tracker item) linking to the packet;
- `CONTROVERSIAL` adds an `rdfs:comment` and `IAO:0000233`.

```turtle
_:axiom1 a owl:Axiom ;
    owl:annotatedSource <http://purl.obolibrary.org/obo/MONDO_0004979> ;
    owl:annotatedProperty rdfs:subClassOf ;
    owl:annotatedTarget <http://purl.obolibrary.org/obo/MONDO_0005275> ;
    SEPIO:0000124 <http://purl.org/np/RA9876543210> ;
    oboInOwl:source <https://orcid.org/0000-0002-6601-2165> .
```

### sieve validate

```bash
sieve validate (-i <file> | -I <dir>)
```

Validates each file as an `EvidencePacket` against `schema/sieve.yaml`, prints one
line per error and a summary, and exits 1 on any error. It currently fails at import;
use `linkml-validate` as above.

---

## Troubleshooting

### "No module named 'sieve'"

Run `uv sync --group dev`, and run commands through `uv run`.

### "cannot import name ... from 'sieve.datamodel.sieve_models'"

The command is one of the pre-profile ones above.

### "ORCID authentication failed"

Check `ORCID_CLIENT_ID` and `ORCID_CLIENT_SECRET`, or set `SIEVE_DEV_MODE=true`.
