# Workflows

Recipes for authoring and checking packets against the SIEVE profile, and for keeping
the generated artefacts current. If you are new to the packet shape, read the
[Primer](primer.md) first; for every field see the [Data Model](data-model.md).

!!! warning "Ingest, review and export target the pre-profile model"
    Sections 1 to 4 work with the current profile. Sections 5 to 8 (ingest into
    DuckDB, review in the app, RDF / YAML export, ORCID curators) describe the
    application layer, which still targets the pre-profile model and does not run
    against current packets. It is being migrated
    (`issues/issue_migrate_app_to_profile.md`).

---

## 1. Author a packet by hand

A packet is one YAML file per claim: the statement (with its lines, origin and
decisions inlined) and the evidence items the lines refer to, in typed lists. Every
entity has an `id` and a `type`. This synonym claim, copied from OMIM in 2019 and
corroborated by the current OMIM release, is adapted from
`tests/data/profile/valid/c003_spoan_synonym_policy.yaml`:

```yaml
id: sieve:pkt/MONDO_0012297-syn-SPOAN
type: EvidencePacket
version: "2026-10-20"
statement:
  id: sieve:st/MONDO_0012297-syn-SPOAN
  type: SynonymStatement
  subject: MONDO:0012297
  predicate: {code: oboInOwl:hasExactSynonym}
  object: SPOAN syndrome
  review_state: NOT_VERIFIED
  proposing_channel: SOURCE_INGEST
  origin:                              # where the claim came from (not evidence)
    - id: sieve:origin/spoan-omim
      type: OriginEvent
      derivation_type: COPIED_FROM
      source_item: OMIM:609541
      source_label: SPOAN syndrome
      source_release: sieve:release/omim-2019-04-30
      performed_by: [sieve:agent/concordance-pipeline]
      date: "2019-05-02"
  has_evidence_lines:                    # what corroborates it now
    - id: sieve:el/spoan-omim
      type: SieveEvidenceLine
      has_evidence_items: [sieve:ca/omim-609541-syn]
      direction_of_evidence_provided: supports
      strength_of_evidence_provided: strong
      score_of_evidence_provided: 0.9
      computed_by_rule: sieve:rule/synonym-v1.1
      confidence: 1.0
      confidence_basis: DETERMINISTIC
      last_confirmed: "2026-10-01"
      last_confirmed_against: sieve:release/omim-2026-10-01
      contributions:
        - id: sieve:act/spoan-omim
          type: InterpretationActivity
          contributor: sieve:agent/concordance-pipeline
          date: "2026-10-20"
          method_type: COMPUTED_CONCORDANCE
          specified_by: [sieve:method/concordance-workflow]
          read_coverage: STRUCTURED_RECORD
prior_claims:
  - id: sieve:ca/omim-609541-syn
    type: SynonymStatement
    subject: OMIM:609541
    predicate: {code: oboInOwl:hasExactSynonym}
    object: SPOAN syndrome
    reported_in: [OMIM:609541]
    resource: infores:omim
external_records:
  - id: OMIM:609541
    type: ExternalRecord
    resource: infores:omim
    generation_context:
      - {code: "sieve:basis_unknown"}
    record_metadata:
      retrieved_from: infores:omim
      source_release: sieve:release/omim-2026-10-01
      retrieval_date: "2026-10-02"
```

Notes:

- Pick the statement `type` for the claim (`SynonymStatement`, `MappingStatement`,
  ...); it fixes which predicates and which item classes are allowed.
- Lines refer to items by id. Each item goes in the list for its class.
- Rules, releases, agents and methods (`sieve:rule/...`, `sieve:release/...`,
  `infores:...`) are ids in a `SieveRegistry`; see `tests/data/profile/registry.yaml`.
- A new claim usually has no `assertion_decisions` yet. The full test file adds the
  policy-based acceptance and the resolution chain for the OMIM id.
- Quote dates, so linkml-validate reads them as strings.

---

## 2. Validate

Two steps. First the schema, with linkml-validate:

```bash
uv run linkml-validate -s schema/sieve.yaml -C EvidencePacket inbox/my_packet.yaml
uv run linkml-validate -s schema/sieve.yaml -C SieveRegistry  registry.yaml
```

It prints `No issues found`, or one `[ERROR]` line per problem, and exits non-zero on
errors. A statement error inside a packet is reported as "not valid under any of the
given schemas in /statement", because the statement can be any claim type. To see the
specific reason, validate the statement on its own against its class (for example
`-C SynonymStatement` on a file holding only the statement).

Then the profile checks:

```python
import yaml
from sieve.profile_checks import check_packet

packet = yaml.safe_load(open("inbox/my_packet.yaml"))
for issue in check_packet(packet):
    print(issue.severity, issue.code, issue.requirement, issue.message)
```

An empty list means the packet passes. ERRORs are profile violations; WARNINGs are
states that need a person (for example a definition with no evidence and no origin).
Pass `obsolete_terms={...}` to flag obsolete-to-obsolete mappings.

---

## 3. Use the generated Pydantic model

```python
import yaml
from sieve.datamodel import EvidencePacket

packet = EvidencePacket.model_validate(yaml.safe_load(open("inbox/my_packet.yaml")))
type(packet.statement).__name__     # "SynonymStatement"
packet.statement.has_evidence_lines[0].direction_of_evidence_provided
```

The `type` designators select the concrete classes, so no custom loader is needed.

---

## 4. Keep generated artefacts current

After editing `schema/sieve.yaml` or `requirements/traceability.yaml`:

```bash
just gen-pydantic          # regenerate src/sieve/datamodel/sieve_models.py
just gen-traceability      # regenerate docs/requirements-traceability.md
just gen-docs              # regenerate the schema reference in docs/elements/
```

When the Mondo requirements workbook changes, re-extract the TSV. The default path
assumes `sepio-linkml` is checked out next to this repository:

```bash
just extract-requirements
just extract-requirements /path/to/Mondo_Requirements_Collection_Forms.xlsx
```

`tests/test_profile_schema.py` and `tests/test_traceability.py` fail if the checked-in
model or traceability page is stale, if a requirement has no trace entry, or if an
annotated requirement ID does not exist.

---

## 5. Ingest into DuckDB (pre-profile)

`sieve ingest` loaded every `*.yaml` / `*.yml` packet under a directory into DuckDB
(default `data/sieve.duckdb`), stored its JSON, computed its Net Evidence Ratio, and
reported per-file errors without aborting the batch:

```bash
sieve ingest -I inbox/examples/ --db data/sieve.duckdb
```

Re-ingesting a packet with an existing `id` overwrote it. The command currently fails
at import.

---

## 6. Review in the app (pre-profile)

`sieve run` launches the Streamlit app with **Dashboard**, **Review Queue**,
**Ingest** and **Export** pages. An authorised curator (ORCID login, manual ORCID
entry, or `SIEVE_DEV_MODE=true`) could accept or reject individual items and record an
**Accept / Reject / Controversial** decision, which wrote a `CurationDecision` and set
the packet's `status`.

In the profile these become a `LineStatusChange` on a line, an `AssertionDecision`
with route `INDIVIDUAL_SIGN_OFF`, and the statement's `review_state`.

---

## 7. Export to RDF and YAML (pre-profile)

`sieve export` read packet files and emitted RDF (`rdf`/`turtle`/`ttl`, `xml`, `n3`,
`nt`) or combined YAML:

```bash
sieve export -I exports/accepted/ -O rdf -o accepted.ttl
sieve export -I packets/ -O yaml -o combined.yaml
```

Each decided packet became an `owl:Axiom` annotation of the statement, linked back to
the packet via `SEPIO:0000124`. Undecided packets were skipped with a warning. See
[cli.md](cli.md#sieve-export) for the options.

---

## 8. ORCID auth and curators

Who may record decisions in the app is controlled by ORCID identity plus a
`curators.yaml` allow-list (path overridable via `CURATORS_FILE`), matched by ORCID
with or without the `orcid:` prefix:

```yaml
curators:
  - orcid: "0000-0001-2345-6789"
    name: "Dr. Jane Smith"
    role: admin
  - orcid: "0000-0002-3456-7890"
    name: "Dr. John Doe"
    role: curator
```

Modes: ORCID OAuth (`ORCID_CLIENT_ID` / `ORCID_CLIENT_SECRET`, optionally
`ORCID_REDIRECT_URI`, `ORCID_SANDBOX`), manual ORCID entry when OAuth is not
configured, and `SIEVE_DEV_MODE=true`, which bypasses auth. The file is re-read roughly
once a minute. See [ORCID Setup](orcid-setup.md).
