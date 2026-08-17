# Data Model

This is the field-by-field reference for the SIEVE evidence model. For the
concepts and the *why*, read the [Primer](primer.md) first; this page is what the
Primer and [AI Integration](ai-integration.md) pages link to for detail.

SIEVE is defined in two LinkML schemas:

- `schema/sieve.yaml` — the canonical SIEVE model (`id: https://w3id.org/sieve`).
- `schema/sepio_classes.yaml` — a trimmed [SEPIO](https://github.com/monarch-initiative/SEPIO-ontology)
  base that SIEVE imports.

Every SIEVE class extends a SEPIO class, so a SIEVE packet is also valid SEPIO.
All field names are `snake_case`.

!!! note "Everything here is auto-generated too"
    The exhaustive per-class and per-slot pages live under the
    [Schema Reference](elements/index.md). This page is the curated tour; that one
    is the generated source of truth.

## The shape at a glance

```
EvidencePacket                       (tree root)
├── statement            → SieveStatement          subject–predicate–object
├── has_evidence_lines[] → SieveEvidenceLine        one argument each
│     └── has_evidence_items[] → six item types     one piece of info each
├── evidence_synthesis   → EvidenceSynthesis         the reasoned verdict
└── curated_by           → CurationActivity          who reviewed it
```

An entity in SEPIO always carries `id` and `type`. In SIEVE, authors set `type:`
on the statement, each evidence line, and each evidence item so the loader can
dispatch to the right class (see [The `type` discriminator](#the-type-discriminator)).

---

## EvidencePacket

The tree root: one statement, its evidence lines, and the verdict.

| Field | Type | Req | Description |
|-------|------|-----|-------------|
| `id` | uriorcurie | Yes | Unique identifier for this packet (the identifier slot). |
| `statement` | [SieveStatement](#sievestatement) | Yes | The assertion being curated. |
| `status` | [CurationStatus](#curationstatus) | Yes | Workflow status. Defaults to `UNREVIEWED`. |
| `has_evidence_lines` | [SieveEvidenceLine](#sieveevidenceline)[] | No | Evidence lines supporting or disputing the statement. |
| `evidence_synthesis` | [EvidenceSynthesis](#evidencesynthesis) | No | Reasoned synthesis of the evidence. |
| `curated_by` | [CurationActivity](#curationactivity) | No | The activity that reviewed/approved the packet. |
| `created` | date | No | When the packet was created. |
| `updated` | date | No | When the packet was last updated. |

---

## SieveStatement

`is_a` SEPIO **Statement**. A subject–predicate–object assertion. SIEVE adds two
label slots; everything else is inherited from SEPIO Statement.

| Field | Type | Req | Description |
|-------|------|-----|-------------|
| `subject` | string | No | Subject entity (CURIE, e.g. `MONDO:0004979`). *(from Statement)* |
| `predicate` | [Coding](#coding) | No | The relationship, as a structured code. *(from Statement)* |
| `object` | string | No | Object entity (CURIE). *(from Statement)* |
| `statement_text` | string | No | Natural-language rendering of the claim. *(from Statement)* |
| `subject_label` | string | No | Human-readable label for the subject. |
| `object_label` | string | No | Human-readable label for the object. |

Statement also inherits SEPIO scoring/qualifier slots (`direction`, `strength`,
`score`, `qualifier`, `proposition`), but SIEVE keeps scoring on the evidence
lines, not here.

!!! note "Evidence lives on the packet, not the statement"
    SEPIO Statement *can* hold `has_evidence_lines`, but SIEVE keeps them on the
    `EvidencePacket` container. Do not nest evidence under `statement`.

---

## Evidence: lines and items (two levels)

A **line** is one argument and says which way it points and how strongly; its
**items** carry the actual content. "Three papers and a clinician agree" is *one*
supporting line built from *four* items.

### SieveEvidenceLine

`is_a` SEPIO **EvidenceLine**. SIEVE adds nothing; it inherits everything.

| Field | Type | Req | Description |
|-------|------|-----|-------------|
| `has_evidence_items` | [InformationEntity](#the-six-evidence-items)[] | No | The evidence items in this argument. |
| `direction_of_evidence_provided` | string | No | `supports`, `disputes`, or `neutral` (see [EvidenceDirection](#evidencedirection)). |
| `strength_of_evidence_provided` | string | No | Qualitative strength: `strong`, `moderate`, `weak` (see [EvidenceStrength](#evidencestrength)). |
| `score_of_evidence_provided` | float | No | Quantitative strength, 0–1. Used by the [Net Evidence Ratio](primer.md#from-evidence-to-a-score). |

---

## The six evidence items

Every evidence item descends from SEPIO **InformationEntity** and carries the
[CuratedEvidence](#curatedevidence) mixin. Pick the class that matches where the
evidence comes from and set `type:` accordingly.

All items inherit the InformationEntity provenance slots: `is_about`,
`contributions`, `date_authored`, `specified_by`, `derived_from`, `reported_in`,
`sources`, `record_metadata`, plus `id`/`type`/`label`/`description` from Entity.

### SieveDocument

`is_a` SEPIO **Document**. A publication or written source, with a pinned quote.

| Field | Type | Description |
|-------|------|-------------|
| `quote` | string | Relevant verbatim quote from the document. |
| `quote_location` | string | Where the quote is (page, section, figure). |
| `title` | string | Document title. *(from Document)* |
| `pmid` | string | PubMed identifier. *(from Document)* |
| `doi` | string | Digital Object Identifier. *(from Document)* |
| `subtype` | [Coding](#coding), `urls`[] | Document kind and retrieval URLs. *(from Document)* |

### ConcordanceItem

`is_a` SieveEvidenceItem. Evidence that another knowledge source (ontology,
terminology, database) contains a *concordant* assertion.

| Field | Type | Description |
|-------|------|-------------|
| `source_name` | string | Human-readable source name (e.g. "Disease Ontology"). |
| `source_id` | uriorcurie | Identifier of the concordant source. |
| `source_version` | string | Version/release of the source. |
| `source_subject` | uriorcurie | Subject of the concordant assertion in the source. |
| `source_subject_label` | string | Label of that subject. |
| `source_predicate` | uriorcurie | Predicate in the concordant assertion. |
| `source_predicate_label` | string | Label of that predicate. |
| `source_object` | uriorcurie | Object of the concordant assertion. |
| `source_object_label` | string | Label of that object. |
| `mapping_justification` | uriorcurie | How entities were mapped (SSSOM vocabulary, e.g. `semapv:LexicalMatching`). |
| `mapping_set` | uri | SSSOM mapping-set the concordance was drawn from. |

### AgentContribution

`is_a` SieveEvidenceItem. Any human or organizational input. Captures three
orthogonal scoring dimensions: *who* (trust), *how* (channel), *what* (type).

| Field | Type | Description |
|-------|------|-------------|
| `contributor` | [Agent](#agent-provenance) | The person or organization who contributed. |
| `trust_level` | [TrustLevel](#trustlevel) | Authority assigned to the contributor. |
| `channel` | [ContributionChannel](#contributionchannel) | How the contribution was submitted. |
| `contribution_type` | [ContributionType](#contributiontype) | Nature of the contribution (suggestion, review, …). |
| `reference` | uriorcurie | Traceability link (issue, email thread, submission ID). |
| `content` | string | What the contributor actually said/provided. |
| `date` | string | When it was made (ISO 8601 string). |

### ComputationalResult

`is_a` SEPIO **DataItem**. Output of a method or algorithm. The computed
score/result goes in the inherited `value`.

| Field | Type | Description |
|-------|------|-------------|
| `method_name` | string | Human-readable method name. |
| `method_id` | uriorcurie | Method identifier (e.g. an OBI term). |
| `parameters` | string | Parameters (JSON string or `key=value`). |
| `software_version` | string | Version of the software/tool. |
| `value` | string | The primary result, e.g. a confidence score. *(from DataItem)* |
| `subtype` | [Coding](#coding) | Categorizes the computation. *(from DataItem)* |

### SieveDataItem

`is_a` SEPIO **DataItem**. A single data point, when no richer item type fits.

| Field | Type | Description |
|-------|------|-------------|
| `value` | string | The data value (required by DataItem). *(from DataItem)* |
| `subtype`, `unit` | [Coding](#coding) | Data type and unit of measure. *(from DataItem)* |

### SieveStudyResult

`is_a` SEPIO **StudyResult**. Results from a single study.

| Field | Type | Description |
|-------|------|-------------|
| `focus` | string | The subject/experimental unit. *(from StudyResult)* |
| `data_items` | [DataItem](#sievedataitem)[] | Data items in the result. *(from StudyResult)* |
| `source_data_set` | DataSet[] | Larger dataset it derives from. *(from StudyResult)* |

---

## CuratedEvidence

A **mixin** applied to every evidence item above. It grafts SIEVE's
curation-workflow slots (a per-item verdict and an explicit ECO hook) onto the
otherwise SEPIO-pure items. It is SIEVE-specific, not SEPIO.

| Field | Type | Description |
|-------|------|-------------|
| `rating` | [CurationStatus](#curationstatus) | The evidence steward's verdict on this individual item. |
| `eco_code` | uriorcurie | [Evidence & Conclusion Ontology](https://www.evidenceontology.org/) term for the item. |
| `eco_label` | string | Human-readable label of the ECO term. |

## The `type` discriminator

SIEVE evidence items are a union of InformationEntity subclasses. Pydantic's
base-class deserialization would drop subclass fields, so the loader
(`src/sieve/datamodel/loaders.py`) dispatches each item to its concrete class by
its `type:` value **before** validating. Authors must therefore set `type:` on
the statement, every evidence line, and every evidence item.

| `type:` value | Class |
|---------------|-------|
| `SieveStatement` | statement |
| `SieveEvidenceLine` | evidence line |
| `ConcordanceItem` | ConcordanceItem |
| `AgentContribution` | AgentContribution |
| `ComputationalResult` | ComputationalResult |
| `SieveDocument` (or alias `Document`) | SieveDocument |
| `SieveDataItem` (or alias `DataItem`) | SieveDataItem |
| `SieveStudyResult` (or alias `StudyResult`) | SieveStudyResult |

`SieveEvidenceItem` also defines an `evidence_item_type` slot ranged on
[EvidenceItemType](#evidenceitemtype) for explicit polymorphism, but the loader
dispatches on `type:`.

---

## Enums

### CurationStatus

Workflow status of a packet, and per-item `rating`.

| Value | Meaning |
|-------|---------|
| `UNREVIEWED` | Not yet reviewed (default). |
| `ACCEPTED` | Accepted as valid. |
| `REJECTED` | Rejected as invalid. |
| `CONTROVERSIAL` | Conflicting evidence, needs discussion. |

### DecisionType

A curator's decision on a packet (used by [CurationDecision](#curationdecision)).

| Value | Meaning |
|-------|---------|
| `ACCEPT` | Accept the assertion. |
| `REJECT` | Reject the assertion. |
| `CONTROVERSIAL` | Mark controversial for further discussion. |

### EvidenceDirection

Direction of an evidence line (`direction_of_evidence_provided`) and the synthesis.

| Value | Meaning |
|-------|---------|
| `supports` | Evidence supports the statement. |
| `disputes` | Evidence disputes the statement. |
| `neutral` | Evidence is neutral. |

### EvidenceStrength

Qualitative strength of an evidence line (`strength_of_evidence_provided`).

| Value | Meaning |
|-------|---------|
| `strong` | Strong evidence. |
| `moderate` | Moderate evidence. |
| `weak` | Weak evidence. |

### TrustLevel

Authority of an `AgentContribution` contributor. Key scoring dimension.

| Value | Meaning |
|-------|---------|
| `community` | General community member, unknown credentials. |
| `domain_expert` | Trusted member with established reputation. |
| `curator` | Official curator with domain expertise and training. |
| `authority` | Authoritative source (official organization, standards body). |

### ContributionChannel

How an `AgentContribution` was submitted. Affects traceability.

| Value | Meaning |
|-------|---------|
| `issue_tracker` | Public issue tracker (GitHub, GitLab). High traceability. |
| `personal_communication` | Private email/conversation. Low traceability. |
| `direct_submission` | Formal submission to the project. Highest traceability. |
| `public_forum` | Public mailing list or forum. Medium-high traceability. |

### ContributionType

Nature of an `AgentContribution`. Affects evidence weight.

| Value | Meaning |
|-------|---------|
| `suggestion` | Proposal without formal commitment. Lowest weight. |
| `review` | Assessment of existing content. Medium weight. |
| `decision` | Formal decision or determination. High weight. |
| `provision` | Direct provision from an authoritative source. Highest weight. |

### EvidenceItemType

Optional polymorphism tag on `SieveEvidenceItem.evidence_item_type`.

| Value | Maps to |
|-------|---------|
| `DataItem` | SieveDataItem |
| `Document` | SieveDocument |
| `StudyResult` | SieveStudyResult |
| `ConcordanceItem` | ConcordanceItem |
| `ComputationalResult` | ComputationalResult |
| `AgentContribution` | AgentContribution |

---

## Provenance and synthesis

### Agent (provenance)

SEPIO **Agent** — an autonomous actor (person, organization, software).

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Identifier, e.g. an ORCID. *(from Entity)* |
| `name` | string | Given name of the agent. |
| `subtype` | string | Kind of agent (person, organization, software). |

### CurationActivity

`is_a` SEPIO **Contribution**. Work done by an agent (human or AI) during
curation. Referenced from the packet's `curated_by` and the synthesis's
`generated_by`; the DuckDB steward column is derived from its `contributor.id`.

| Field | Type | Description |
|-------|------|-------------|
| `contributor` | [Agent](#agent-provenance) | Who did the work. *(from Contribution)* |
| `activity_type` | [Coding](#coding)[] | Role/type of activity. *(from Contribution)* |
| `date` | string | Date completed (ISO 8601 string). *(from Activity)* |
| `performed_by` | [Agent](#agent-provenance)[] | Agents who executed the activity. *(from Activity)* |
| `timestamp` | datetime | When performed (datetime precision). |
| `used` | string[] | Inputs used (prompt versions, tools). |
| `pull_request` | uriorcurie | Associated GitHub PR URL. |
| `issue` | uriorcurie | Associated GitHub issue URL. |
| `created_with` | uriorcurie | Tool/software used (e.g. a Protégé URI). |

### EvidenceSynthesis

The reasoned verdict over all evidence lines.

| Field | Type | Req | Description |
|-------|------|-----|-------------|
| `summary` | string | Yes | Textual explanation of the conclusion. |
| `score` | [Score](#score) | No | Aggregated score. |
| `direction` | [EvidenceDirection](#evidencedirection) | No | Overall direction — supports/disputes/neutral. |
| `cited_evidence` | string[] | No | IDs of evidence lines cited in the synthesis. |
| `generated_by` | [CurationActivity](#curationactivity) | No | The activity that produced the synthesis. |

### Score

| Field | Type | Req | Description |
|-------|------|-----|-------------|
| `value` | float | Yes | Numeric score value. |
| `description` | string | No | How the score was computed. |

### Coding

SEPIO **Coding** — a structured code, used for `predicate` and `subtype` slots.

| Field | Type | Description |
|-------|------|-------------|
| `code` | string | The code (CURIE preferred, e.g. `rdfs:subClassOf`). |
| `label` | string | Human-readable name of the concept. |
| `system` | string | Terminology/code system that defined the code. |
| `system_version` | string | Version of that system. |

### CurationDecision

A standalone audit record of one curator decision on a packet. One row per
decision, preserving history — richer than the single `curated_by` activity.
SIEVE-specific; stored in its own DuckDB table.

| Field | Type | Req | Description |
|-------|------|-----|-------------|
| `id` | string | Yes | Decision identifier. |
| `packet_id` | uriorcurie | Yes | The `EvidencePacket.id` this applies to. |
| `curator` | uriorcurie | Yes | ORCID of the deciding curator. |
| `curator_name` | string | No | Curator display name. |
| `decision` | [DecisionType](#decisiontype) | Yes | The decision. |
| `rationale` | string | No | Explanation (required for rejections). |
| `certainty` | float | No | Confidence in the decision, 0–1. |
| `decided_at` | datetime | Yes | When the decision was made. |

---

## Storage

Packets are stored in DuckDB (`src/sieve/store.py`). The full packet is kept as
JSON with a few columns promoted for querying.

**`evidence_packets`** — one row per packet:

| Column | Type | Source |
|--------|------|--------|
| `id` | VARCHAR (PK) | `packet.id` |
| `subject_id` | VARCHAR | `statement.subject` |
| `predicate` | VARCHAR | `statement.predicate.code` |
| `object_id` | VARCHAR | `statement.object` |
| `status` | VARCHAR | `packet.status` |
| `evidence_score` | DOUBLE | computed Net Evidence Ratio |
| `evidence_steward` | VARCHAR | `curated_by.contributor.id` |
| `created` | VARCHAR | `packet.created` |
| `updated` | VARCHAR | `packet.updated` |
| `packet_json` | JSON | full packet (`serialize_as_any`, so polymorphic item fields survive) |

**`packet_decisions`** — one row per [CurationDecision](#curationdecision):

| Column | Type |
|--------|------|
| `id` | VARCHAR (PK) |
| `packet_id` | VARCHAR |
| `curator` | VARCHAR |
| `curator_name` | VARCHAR |
| `decision` | VARCHAR |
| `rationale` | VARCHAR |
| `certainty` | DOUBLE |
| `decided_at` | VARCHAR |

---

## A complete example

A minimal, valid packet (from `tests/data/valid/example_packet.yaml`). Note the
`type:` on the statement, the line, and every item.

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

Validate and ingest:

```bash
sieve validate -I inbox/examples/
sieve ingest   -I inbox/examples/
```

---

## Full generated reference and SEPIO alignment

For the exhaustive, auto-generated per-class and per-slot documentation — every
inherited slot, range, and cardinality — see the [Schema Reference](elements/index.md).

Because each SIEVE class `is_a` a SEPIO class (`SieveStatement` → `Statement`,
`SieveEvidenceLine` → `EvidenceLine`, the six items → `InformationEntity`, …),
every packet carries SEPIO semantics through the generated `class_uri`/`slot_uri`
mappings. That is what lets an accepted packet export as valid SEPIO RDF, so
evidence means the same thing across Monarch. See the [Primer](primer.md) for the
end-to-end story.
