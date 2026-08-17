# Authoring Packets as an AI Agent

This page is for AI agents (LLMs, autonomous pipelines) that **produce evidence
packets** for SIEVE. It covers only the AI-specific parts: how to author a valid
packet and how to exercise judgment honestly.

It deliberately does **not** re-teach the data model. Read these first:

- [SIEVE in Plain Terms](primer.md) — the concepts (statement, evidence lines,
  items, verdict).
- [Data Model](data-model.md) — the authoritative, field-by-field reference.

## What you produce

An AI agent's output is a single **valid `EvidencePacket` YAML** in the current
SEPIO/SIEVE shape: one `statement`, a list of `has_evidence_lines`, and each line
a list of `has_evidence_items`. Every item carries a `type:` discriminator that
says which kind of evidence it is. Leave `status: UNREVIEWED` — a human makes the
final decision.

See [Data Model](data-model.md) for every field; this page assumes you already
know the shape.

## Choosing an item `type:`

Every evidence item **must** have a `type:`. Pick from these six:

| `type:` | Use when the evidence is… |
|---------|---------------------------|
| `SieveDocument` | a publication, guideline, or textbook you can quote (`pmid`, `title`, `quote`, `quote_location`). |
| `ConcordanceItem` | another ontology, terminology, or database that already makes the aligned assertion. |
| `AgentContribution` | a person or organization who weighed in (expert review, curator note, community suggestion). |
| `ComputationalResult` | the output of a method or algorithm — including your own analysis (`method_name`, `value`, `parameters`). |
| `SieveDataItem` | a raw data record that stands as evidence on its own. |
| `SieveStudyResult` | a reported result from a study or experiment. |

When your own analysis *is* the evidence, use `ComputationalResult` and name the
method honestly — do not dress an LLM summary up as a `SieveDocument`.

## Direction, strength, score

Each **evidence line** declares which way it points and how strongly. Set these
on the line, not the item:

- `direction_of_evidence_provided`: `supports` | `disputes` | `neutral`
  (lowercase). Add a line with `disputes` when evidence points against the
  statement — do not silently drop it.
- `strength_of_evidence_provided`: `strong` | `moderate` | `weak` — your
  qualitative read of the argument.
- `score_of_evidence_provided`: a number in `0–1` used for scoring. Be
  conservative; reserve values near `1.0` for direct, unambiguous evidence.

Set these to reflect the *evidence*, not your eagerness for a particular verdict.
An item may also carry an optional curator `rating` and an `eco_code`.

## A minimal valid packet

```yaml
id: sieve:pkt_asthma_0001
status: UNREVIEWED
statement:
  id: stmt_asthma_0001
  type: SieveStatement
  subject: MONDO:0004979
  subject_label: asthma
  predicate:
    code: rdfs:subClassOf
    label: subClassOf
  object: MONDO:0005275
  object_label: respiratory system disorder
  statement_text: asthma subClassOf respiratory system disorder
has_evidence_lines:
  - id: line_0001
    type: SieveEvidenceLine
    direction_of_evidence_provided: supports
    strength_of_evidence_provided: strong
    score_of_evidence_provided: 0.9
    has_evidence_items:
      - id: ev_concordance_0001
        type: ConcordanceItem
        source_name: Disease Ontology
        source_id: DOID:2841
        rating: ACCEPTED
        eco_code: ECO:0000269
      - id: ev_document_0001
        type: SieveDocument
        title: Example study
        pmid: "12345678"
        quote: asthma is a chronic respiratory disease
        rating: ACCEPTED
```

Every entity (`statement`, each line, each item) needs an `id` and a `type`.

## Validating your output

Write packets to a directory and run:

```bash
sieve validate -I inbox/examples/      # validate every packet in a directory
sieve validate -i my_packet.yaml       # validate one file
```

`validate` reports each file as `OK` or lists the schema errors and exits
non-zero if anything fails. Always validate before handing packets off.

## DO / DON'T

**DO**

- Set a `type:` on every evidence item and an `id` + `type` on every entity.
- Quote source text **verbatim** in `SieveDocument.quote`.
- Cite real, resolvable identifiers (real `PMID`s, real ontology CURIEs).
- Add a `disputes` line when the evidence genuinely cuts against the statement.
- Leave `status: UNREVIEWED` and let a human decide.

**DON'T**

- Don't fabricate references, PMIDs, or concordances that don't exist.
- Don't overstate — inflated `strength`/`score` values are worse than honest weak
  ones.
- Don't use the deleted flat model (`assertion`, flat `evidence[]`,
  `evidence_type`, `direction: CONTRADICTS`, `evidence_strength`). The current
  shape is `statement` + `has_evidence_lines` → `has_evidence_items` with `type:`.
- Don't pass your own LLM analysis off as a publication — use
  `ComputationalResult`.
