# Data Model

SIEVE uses a LinkML schema (`schema/curation_model.yaml`) to define its data structures. This document describes the complete data model and provides examples.

## Overview

The data model centers on the **CurationRecord** class, which represents an evidence packet containing an assertion and its supporting evidence.

```
CurationRecord
├── id: string
├── status: CurationStatus
├── assertion: Assertion
├── provenance: AssertionProvenance
├── evidence: Evidence[]
├── evidence_synthesis: EvidenceSynthesis
├── evidence_steward: string (ORCID)
└── confidence: float (0-1)
```

## Core Classes

### CurationRecord

The main container for an evidence packet.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | uriorcurie | Yes | Unique identifier (e.g., nanopub URI) |
| `status` | CurationStatus | Yes | Review status (default: UNREVIEWED) |
| `last_updated` | date | No | Date of last modification |
| `assertion` | Assertion | Yes | The statement being curated |
| `provenance` | AssertionProvenance | No | Origin and attribution |
| `evidence` | Evidence[] | No | List of evidence items |
| `evidence_synthesis` | EvidenceSynthesis | No | Summary synthesis of evidence |
| `evidence_steward` | uriorcurie | No | ORCID of final decision maker |
| `confidence` | float | No | Steward's confidence (0.0-1.0) |

**Example:**
```yaml
id: http://purl.org/np/RA9876543210
status: ACCEPTED
last_updated: "2024-01-20"
evidence_steward: orcid:0000-0002-6601-2165
confidence: 0.95
assertion:
  subject_id: MONDO:0004979
  predicate: rdfs:subClassOf
  object_id: MONDO:0005275
```

### Assertion

The ontological statement being evaluated.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `subject_id` | uriorcurie | Yes | Subject term CURIE |
| `subject_label` | string | No | Human-readable subject label |
| `predicate` | uriorcurie | Yes | Relationship type CURIE |
| `predicate_label` | string | No | Human-readable predicate label |
| `object_id` | uriorcurie | Yes | Object term CURIE |
| `object_label` | string | No | Human-readable object label |
| `display_text` | string | No | Full human-readable rendering |

**Example:**
```yaml
assertion:
  subject_id: MONDO:0004979
  subject_label: asthma
  predicate: rdfs:subClassOf
  predicate_label: subClassOf
  object_id: MONDO:0005275
  object_label: respiratory system disorder
  display_text: "asthma subClassOf respiratory system disorder"
```

### Evidence (Abstract Base)

Base class for all evidence types. All evidence items share these common fields:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | No | Unique evidence item identifier |
| `evidence_type` | EvidenceType | Yes | Type discriminator |
| `direction` | EvidenceDirection | No | SUPPORTS/CONTRADICTS/UNCERTAIN |
| `evidence_strength` | float | No | Strength from 0.0 (weak) to 1.0 (strong) |
| `rating` | CurationStatus | No | Steward's rating of this evidence |
| `eco_code` | uriorcurie | No | Evidence ontology code |
| `eco_label` | string | No | ECO term label |
| `description` | string | No | Human-readable description |

### ConcordanceEvidence

Cross-ontology or cross-terminology agreement evidence.

| Field | Type | Description |
|-------|------|-------------|
| `source` | uriorcurie | PURL of the concordant source |
| `source_name` | string | Human-readable source name |
| `source_type` | SourceType | ONTOLOGY/TERMINOLOGY/DATABASE/OTHER |
| `predicate_id` | uriorcurie | Predicate used in source |
| `source_subject_id` | uriorcurie | Subject ID in source ontology |
| `source_subject_label` | string | Subject label in source |
| `source_object_id` | uriorcurie | Object ID in source ontology |
| `source_object_label` | string | Object label in source |
| `mapping_set` | uri | SSSOM mapping set reference |

**Example:**
```yaml
- id: ev-concordance-icd10
  evidence_type: CONCORDANCE
  direction: SUPPORTS
  evidence_strength: 0.9
  eco_code: ECO:0000204
  eco_label: similarity evidence
  source: https://bioportal.bioontology.org/ontologies/ICD10CM
  source_name: ICD-10-CM
  source_type: TERMINOLOGY
  predicate_id: rdfs:subClassOf
  source_subject_id: ICD10CM:J45
  source_subject_label: Asthma
  source_object_id: ICD10CM:J00-J99
  source_object_label: Diseases of the respiratory system
  mapping_set: https://w3id.org/sssom/mappings/mondo-icd10.sssom.tsv
```

### LiteratureEvidence

Evidence from published literature.

| Field | Type | Description |
|-------|------|-------------|
| `publication_id` | uriorcurie | Publication identifier (e.g., PMID:12345) |
| `publication_title` | string | Title of the publication |
| `quoted_text` | string | Verbatim excerpt supporting the assertion |
| `quote_location` | string | Section/page reference |
| `explanation` | string | How the quoted text supports the assertion |

**Example:**
```yaml
- id: ev-literature-1
  evidence_type: LITERATURE
  direction: SUPPORTS
  evidence_strength: 0.95
  eco_code: ECO:0000006
  eco_label: experimental evidence
  publication_id: PMID:28884740
  publication_title: "Global Strategy for Asthma Management and Prevention"
  quoted_text: >-
    Asthma is a heterogeneous disease, usually characterized by chronic airway
    inflammation. It is defined by the history of respiratory symptoms...
  quote_location: "Chapter 1, Definition, page 14"
  explanation: >-
    This text explicitly defines asthma as a disease characterized by respiratory
    symptoms, directly supporting its classification as a respiratory disorder.
```

### ExpertReviewEvidence

Evidence from domain expert validation.

| Field | Type | Description |
|-------|------|-------------|
| `reviewer_orcid` | uriorcurie | Reviewer's ORCID |
| `reviewer_name` | string | Reviewer's name |
| `reviewer_affiliation` | string | Reviewer's institution |
| `reviewed_at` | date | Date of review |
| `issue` | uriorcurie | GitHub issue URL for discussion |

**Example:**
```yaml
- id: ev-expert-review
  evidence_type: EXPERT_REVIEW
  direction: SUPPORTS
  evidence_strength: 0.8
  eco_code: ECO:0000218
  eco_label: manual assertion
  description: "Clinical pulmonologist review confirming classification"
  reviewer_orcid: orcid:0000-0003-4567-8901
  reviewer_name: Dr. Sarah Chen
  reviewer_affiliation: Johns Hopkins Medicine
  reviewed_at: "2024-01-20"
  issue: https://github.com/monarch-initiative/mondo/issues/7890
```

### ComputationalEvidence

Evidence from algorithmic or computational methods.

| Field | Type | Description |
|-------|------|-------------|
| `method` | string | Name/description of the method |
| `method_uri` | uriorcurie | URI identifying the method |
| `confidence_score` | float | Confidence score from the method |
| `parameters` | string | Parameters used in computation |

**Example:**
```yaml
- id: ev-ai-research
  evidence_type: COMPUTATIONAL
  direction: SUPPORTS
  evidence_strength: 0.75
  eco_code: ECO:0008006
  eco_label: computational evidence
  description: "AI analysis of classification in medical literature"
  method: ChatGPT Deep Research
  method_uri: https://openai.com/chatgpt
  confidence_score: 0.92
  parameters: >-
    Prompt: "Analyze the medical literature to determine whether asthma
    should be classified as a respiratory system disorder..."
```

### EvidenceSynthesis

A summary synthesis of all evidence for an assertion.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `summary` | string | Yes | Textual synthesis of the evidence |
| `confidence` | float | Yes | Confidence score (0.0-1.0) |

**Example:**
```yaml
evidence_synthesis:
  summary: >
    After reviewing multiple lines of evidence, including cross-ontology
    concordance with ICD-10, published literature, and expert clinical review,
    the classification of asthma as a respiratory system disorder is well-supported.
  confidence: 0.95
```

### AssertionProvenance

Origin and attribution information for the assertion.

| Field | Type | Description |
|-------|------|-------------|
| `attributed_to` | uriorcurie[] | ORCIDs of original creators |
| `generated_at` | date | When the assertion was created |
| `source_version` | string | Version of source (e.g., "Mondo 2024-05-01") |
| `source_uri` | uri | URI of the source ontology/database |
| `generated_by` | CurationActivity | Activity that generated this assertion |

### CurationActivity

A curation activity that generated or modified an assertion.

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Activity identifier |
| `description` | string | Human-readable description |
| `associated_with` | uriorcurie[] | ORCIDs/URIs of people/organizations |
| `started_at` | date | Activity start date |
| `ended_at` | date | Activity end date |
| `created_with` | uriorcurie | Tool URI (e.g., Protege) |
| `pull_request` | uriorcurie | Associated GitHub PR URL |

### CurationDecision

A curator's decision on a CurationRecord.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | Yes | Decision identifier |
| `record_id` | string | Yes | Reference to CurationRecord.id |
| `curator_orcid` | uriorcurie | Yes | Curator's ORCID |
| `curator_name` | string | No | Curator's display name |
| `decision` | DecisionType | Yes | ACCEPT/REJECT/CONTROVERSIAL |
| `certainty` | float | No | Confidence in decision (0.0-1.0, default: 1.0) |
| `rationale` | string | No | Explanation for the decision |
| `decided_at` | datetime | Yes | Timestamp of decision |

## Enumerations

### CurationStatus

Status of a curation record or evidence rating.

| Value | Description |
|-------|-------------|
| `UNREVIEWED` | Not yet reviewed (default) |
| `ACCEPTED` | Approved by curator |
| `REJECTED` | Rejected by curator |
| `CONTROVERSIAL` | Conflicting opinions or requires discussion |

### DecisionType

Type of curator decision.

| Value | Description |
|-------|-------------|
| `ACCEPT` | Accept the assertion |
| `REJECT` | Reject the assertion |
| `CONTROVERSIAL` | Mark as controversial |

### EvidenceType

Discriminator for evidence subtypes.

| Value | Meaning | Maps To |
|-------|---------|---------|
| `CONCORDANCE` | Cross-ontology agreement | ConcordanceEvidence |
| `LITERATURE` | Published literature | LiteratureEvidence |
| `EXPERT_REVIEW` | Domain expert validation | ExpertReviewEvidence |
| `COMPUTATIONAL` | Algorithmic evidence | ComputationalEvidence |
| `OTHER` | Other evidence type | Evidence (base) |

### EvidenceDirection

Whether evidence supports or contradicts the assertion.

| Value | Description |
|-------|-------------|
| `SUPPORTS` | Evidence supports the assertion |
| `CONTRADICTS` | Evidence contradicts the assertion |
| `UNCERTAIN` | Direction is uncertain or neutral |

### SourceType

Type of concordance source.

| Value | Description |
|-------|-------------|
| `ONTOLOGY` | An ontology source |
| `TERMINOLOGY` | A terminology or classification system |
| `DATABASE` | A database or knowledge base |
| `OTHER` | Other source type |

## Complete Example

Here is a complete evidence packet example:

```yaml
id: http://purl.org/np/RA9876543210
status: ACCEPTED
last_updated: "2024-01-20"
evidence_steward: orcid:0000-0002-6601-2165
confidence: 0.95

assertion:
  subject_id: MONDO:0004979
  subject_label: asthma
  predicate: rdfs:subClassOf
  predicate_label: subClassOf
  object_id: MONDO:0005275
  object_label: respiratory system disorder
  display_text: "asthma subClassOf respiratory system disorder"

provenance:
  attributed_to:
    - orcid:0000-0002-6601-2165
  generated_at: "2020-06-15"
  source_version: "2025-10-08"
  source_uri: http://purl.obolibrary.org/obo/mondo/releases/2025-10-08/mondo.owl
  generated_by:
    id: activity:mondo-asthma-curation-2020
    description: Mondo disease ontology curation
    associated_with:
      - orcid:0000-0002-6601-2165
    started_at: "2020-06-10"
    ended_at: "2020-06-15"
    created_with: https://protege.stanford.edu/
    pull_request: https://github.com/monarch-initiative/mondo/pull/2345

evidence_synthesis:
  summary: >
    After reviewing multiple lines of evidence, including cross-ontology
    concordance, literature, and expert review, the classification is well-supported.
  confidence: 0.95

evidence:
  - id: ev-concordance-icd10
    evidence_type: CONCORDANCE
    direction: SUPPORTS
    evidence_strength: 0.9
    rating: ACCEPTED
    source_name: ICD-10-CM
    source_type: TERMINOLOGY
    source_subject_id: ICD10CM:J45

  - id: ev-literature-1
    evidence_type: LITERATURE
    direction: SUPPORTS
    evidence_strength: 0.95
    rating: ACCEPTED
    publication_id: PMID:28884740
    publication_title: "Global Strategy for Asthma Management"

  - id: ev-expert-review
    evidence_type: EXPERT_REVIEW
    direction: SUPPORTS
    evidence_strength: 0.8
    reviewer_orcid: orcid:0000-0003-4567-8901
    reviewer_name: Dr. Sarah Chen
```

## Validation

Evidence packets can be validated against the LinkML schema:

```bash
sieve validate -i packet.yaml
sieve validate -I packets/
```

The validator checks:
- Required fields are present
- Field types are correct
- Enum values are valid
- Numeric constraints (e.g., 0.0 <= confidence <= 1.0)
