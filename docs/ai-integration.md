# AI Integration Guide

This document provides guidance for AI agents (LLMs, autonomous systems) working with SIEVE. It explains the data model, expected behaviors, and integration patterns.

## Understanding SIEVE's Purpose

SIEVE (Scientific Evidence Evaluation & Verification Environment) manages **evidence packets** that support or contradict ontological assertions. An ontological assertion is a statement about the classification or relationship between concepts, such as:

> "asthma is a subclass of respiratory system disorder"

AI agents typically interact with SIEVE to:
1. **Generate** evidence packets from analysis of literature, ontologies, or other sources
2. **Validate** evidence packets against the schema
3. **Process** or transform evidence data
4. **Export** curated evidence to RDF for ontology integration

## Core Data Structures

### Evidence Packet Structure

An evidence packet is a YAML document with this structure:

```yaml
# Required fields
id: <unique-identifier>           # URI or CURIE
status: <UNREVIEWED|ACCEPTED|REJECTED|CONTROVERSIAL>
assertion:                        # The claim being evaluated
  subject_id: <CURIE>            # e.g., MONDO:0004979
  predicate: <CURIE>             # e.g., rdfs:subClassOf
  object_id: <CURIE>             # e.g., MONDO:0005275

# Optional but recommended
evidence: []                      # List of evidence items
provenance: {}                    # Origin information
evidence_synthesis: {}            # Summary synthesis
evidence_steward: <ORCID>        # Who made final decision
confidence: <0.0-1.0>            # Decision confidence
```

### Evidence Item Structure

Each evidence item follows a type-specific structure:

```yaml
# Common fields (all evidence types)
id: <identifier>
evidence_type: <CONCORDANCE|LITERATURE|EXPERT_REVIEW|COMPUTATIONAL|OTHER>
direction: <SUPPORTS|CONTRADICTS|UNCERTAIN>
evidence_strength: <0.0-1.0>     # How strong is this evidence?
rating: <UNREVIEWED|ACCEPTED|REJECTED|CONTROVERSIAL>  # Curator's rating
description: <text>

# Type-specific fields vary by evidence_type
```

## Evidence Type Specifications

### CONCORDANCE Evidence

Use for cross-ontology or cross-terminology agreement:

```yaml
evidence_type: CONCORDANCE
direction: SUPPORTS
evidence_strength: 0.9
source: https://bioportal.bioontology.org/ontologies/ICD10CM
source_name: ICD-10-CM
source_type: TERMINOLOGY  # ONTOLOGY, TERMINOLOGY, DATABASE, OTHER
source_subject_id: ICD10CM:J45
source_subject_label: Asthma
source_object_id: ICD10CM:J00-J99
source_object_label: Diseases of the respiratory system
mapping_set: https://w3id.org/sssom/mappings/mondo-icd10.sssom.tsv
```

**When to use**: When another authoritative source (ontology, terminology, classification system) contains an equivalent or analogous relationship.

**Key considerations**:
- `source_type` should reflect the nature of the source
- Include `mapping_set` if mappings come from SSSOM
- `source_subject_id` and `source_object_id` should be CURIEs from the source

### LITERATURE Evidence

Use for published literature citations:

```yaml
evidence_type: LITERATURE
direction: SUPPORTS
evidence_strength: 0.95
publication_id: PMID:28884740
publication_title: "Global Strategy for Asthma Management"
quoted_text: >-
  Asthma is a heterogeneous disease, usually characterized by chronic airway
  inflammation. It is defined by the history of respiratory symptoms...
quote_location: "Chapter 1, Definition, page 14"
explanation: >-
  This text explicitly defines asthma as a disease characterized by respiratory
  symptoms, directly supporting its classification as a respiratory disorder.
```

**When to use**: When citing peer-reviewed publications, clinical guidelines, or authoritative textbooks.

**Key considerations**:
- Always include `publication_id` (prefer PMID, DOI)
- `quoted_text` should be verbatim from the source
- `explanation` connects the quote to the assertion
- `evidence_strength` should reflect publication quality and relevance

### EXPERT_REVIEW Evidence

Use for domain expert assessments:

```yaml
evidence_type: EXPERT_REVIEW
direction: SUPPORTS
evidence_strength: 0.8
reviewer_orcid: orcid:0000-0003-4567-8901
reviewer_name: Dr. Sarah Chen
reviewer_affiliation: Johns Hopkins Medicine
reviewed_at: "2024-01-20"
issue: https://github.com/monarch-initiative/mondo/issues/7890
description: "Clinical pulmonologist review confirming classification"
```

**When to use**: When a domain expert has explicitly reviewed and commented on the assertion.

**Key considerations**:
- `reviewer_orcid` should be a valid ORCID
- `issue` can link to GitHub discussions
- Expert credentials (affiliation) add credibility

### COMPUTATIONAL Evidence

Use for algorithmic or AI-generated analysis:

```yaml
evidence_type: COMPUTATIONAL
direction: SUPPORTS
evidence_strength: 0.75
method: ChatGPT Deep Research
method_uri: https://openai.com/chatgpt
confidence_score: 0.92
parameters: >-
  Prompt: "Analyze the medical literature to determine whether asthma
  should be classified as a respiratory system disorder..."

  Summary: Analysis of 47 sources found unanimous consensus...
description: "AI analysis of asthma classification in medical literature"
```

**When to use**: When evidence comes from computational methods, ML models, or AI analysis.

**Key considerations**:
- Clearly document the `method` and parameters used
- Include the `confidence_score` from the method if available
- Be transparent about limitations in the `description`

## AI Agent Workflows

### Workflow 1: Evidence Generation

AI agents generating evidence packets should:

1. **Structure output as valid YAML** following the schema
2. **Use appropriate evidence types** for each source
3. **Set reasonable evidence_strength values**:
   - 0.9-1.0: Very strong, direct evidence
   - 0.7-0.9: Strong supporting evidence
   - 0.5-0.7: Moderate evidence
   - 0.3-0.5: Weak evidence
   - 0.0-0.3: Very weak or tangential
4. **Include all available metadata** (IDs, labels, sources)
5. **Set status to UNREVIEWED** for human review

Example generation prompt pattern:

```
Generate a SIEVE evidence packet for the assertion:
"{subject_label} ({subject_id}) {predicate} {object_label} ({object_id})"

Search for:
1. Cross-ontology concordance (ICD-10, SNOMED CT, DOID, etc.)
2. Literature evidence (PubMed citations)
3. Expert consensus (clinical guidelines)

Output as YAML following the SIEVE schema.
```

### Workflow 2: Evidence Synthesis

AI agents creating `evidence_synthesis` blocks should:

1. **Summarize all evidence items** objectively
2. **Acknowledge contradicting evidence** if present
3. **Calculate a weighted assessment**
4. **Express appropriate uncertainty**

Example synthesis:

```yaml
evidence_synthesis:
  summary: >
    After reviewing 5 evidence items (4 supporting, 1 contradicting),
    the classification of asthma as a respiratory system disorder is
    well-supported. Supporting evidence includes concordance with ICD-10
    and SNOMED CT, peer-reviewed literature defining asthma as a respiratory
    condition, and expert clinical review. The single contradicting evidence
    from Disease Ontology (which classifies asthma under sensory system disease)
    appears to be an outlier not supported by other sources.
  confidence: 0.92
```

### Workflow 3: Validation and Quality Check

AI agents should validate generated packets:

```bash
# Validate schema compliance
sieve validate -i generated_packet.yaml
```

Check for common issues:
- Missing required fields
- Invalid CURIEs (should be `PREFIX:localId`)
- Evidence strength outside 0.0-1.0 range
- Invalid enum values

### Workflow 4: Batch Processing

For processing multiple assertions:

```python
from sieve.ingest import parse_curation_record
from sieve.validators import validate_json_schema
import yaml

def process_assertion(assertion_data, evidence_sources):
    """Generate and validate an evidence packet."""

    packet = {
        "id": generate_id(assertion_data),
        "status": "UNREVIEWED",
        "assertion": assertion_data,
        "evidence": evidence_sources,
    }

    # Validate before output
    report = validate_json_schema(packet)
    if any(r.severity.value <= 2 for r in report.results):
        raise ValueError(f"Invalid packet: {report.results}")

    return packet
```

## Integration Patterns

### Pattern 1: Evidence Aggregator

An AI agent that collects evidence from multiple sources:

```
Input: Ontology axiom to evaluate
Process:
  1. Query cross-reference databases for concordance
  2. Search PubMed for relevant literature
  3. Check existing expert reviews/GitHub issues
  4. Run computational analysis if appropriate
Output: SIEVE evidence packet with aggregated evidence
```

### Pattern 2: Evidence Synthesizer

An AI agent that summarizes evidence:

```
Input: SIEVE evidence packet with multiple evidence items
Process:
  1. Analyze each evidence item
  2. Weigh by evidence_strength and direction
  3. Identify consensus and conflicts
  4. Generate natural language synthesis
Output: Updated packet with evidence_synthesis block
```

### Pattern 3: Curation Assistant

An AI agent that assists human curators:

```
Input: Evidence packet for review
Process:
  1. Summarize key evidence points
  2. Highlight potential issues or conflicts
  3. Suggest decision with rationale
  4. Flag items needing closer human review
Output: Curation recommendations (human makes final decision)
```

## Best Practices for AI Agents

### DO:

1. **Be transparent** about AI-generated content
   - Set `evidence_type: COMPUTATIONAL` for AI analysis
   - Document the method and parameters used

2. **Express uncertainty appropriately**
   - Use `evidence_strength` to indicate confidence
   - Include caveats in descriptions

3. **Cite sources accurately**
   - Verify publication IDs exist
   - Quote text verbatim when possible

4. **Follow the schema strictly**
   - Use valid CURIEs (PREFIX:localId)
   - Use correct enum values
   - Include required fields

5. **Support human review**
   - Set `status: UNREVIEWED` for human verification
   - Provide clear explanations
   - Flag uncertain items

### DON'T:

1. **Don't fabricate evidence**
   - Only cite real publications
   - Don't invent concordance that doesn't exist

2. **Don't overstate confidence**
   - Be conservative with `evidence_strength`
   - Acknowledge limitations

3. **Don't bypass human review**
   - New packets should be UNREVIEWED
   - Final decisions require human judgment

4. **Don't ignore contradicting evidence**
   - Include evidence with `direction: CONTRADICTS`
   - Document conflicts in synthesis

## CURIE Reference

Common prefixes used in SIEVE:

| Prefix | Expansion | Example |
|--------|-----------|---------|
| `MONDO` | http://purl.obolibrary.org/obo/MONDO_ | MONDO:0004979 |
| `DOID` | http://purl.obolibrary.org/obo/DOID_ | DOID:2841 |
| `HP` | http://purl.obolibrary.org/obo/HP_ | HP:0002099 |
| `ECO` | http://purl.obolibrary.org/obo/ECO_ | ECO:0000006 |
| `PMID` | https://pubmed.ncbi.nlm.nih.gov/ | PMID:28884740 |
| `orcid` | https://orcid.org/ | orcid:0000-0001-2345-6789 |
| `rdfs` | http://www.w3.org/2000/01/rdf-schema# | rdfs:subClassOf |
| `owl` | http://www.w3.org/2002/07/owl# | owl:equivalentClass |

## Error Handling

Common errors and solutions:

| Error | Cause | Solution |
|-------|-------|----------|
| `'assertion' is a required property` | Missing assertion block | Add assertion with subject_id, predicate, object_id |
| `'UNKNOWN' is not valid under any of the given schemas` | Invalid enum value | Use valid status: UNREVIEWED, ACCEPTED, REJECTED, CONTROVERSIAL |
| `evidence_strength must be <= 1` | Value out of range | Use value between 0.0 and 1.0 |
| `Invalid CURIE format` | Malformed identifier | Use PREFIX:localId format |

## Example Complete Packet

Here's a complete, well-formed evidence packet suitable for AI generation:

```yaml
id: http://example.org/evidence/mondo-0004979-respiratory
status: UNREVIEWED

assertion:
  subject_id: MONDO:0004979
  subject_label: asthma
  predicate: rdfs:subClassOf
  predicate_label: subClassOf
  object_id: MONDO:0005275
  object_label: respiratory system disorder
  display_text: "asthma subClassOf respiratory system disorder"

evidence:
  - id: ev-concordance-001
    evidence_type: CONCORDANCE
    direction: SUPPORTS
    evidence_strength: 0.9
    eco_code: ECO:0000204
    description: "ICD-10-CM places asthma under respiratory diseases"
    source_name: ICD-10-CM
    source_type: TERMINOLOGY
    source_subject_id: ICD10CM:J45
    source_object_id: ICD10CM:J00-J99

  - id: ev-literature-001
    evidence_type: LITERATURE
    direction: SUPPORTS
    evidence_strength: 0.95
    eco_code: ECO:0000006
    publication_id: PMID:28884740
    publication_title: "Global Strategy for Asthma Management (GINA)"
    quoted_text: "Asthma is characterized by chronic airway inflammation"
    explanation: "Defines asthma in respiratory terms"

  - id: ev-computational-001
    evidence_type: COMPUTATIONAL
    direction: SUPPORTS
    evidence_strength: 0.75
    method: Literature Analysis
    method_uri: https://example.org/analysis-tool
    confidence_score: 0.88
    description: "Automated analysis of 50 publications confirms classification"

evidence_synthesis:
  summary: >
    Multiple lines of evidence support classifying asthma as a respiratory
    system disorder: concordance with ICD-10 classification, GINA guidelines
    definition, and computational literature analysis. No significant
    contradicting evidence found.
  confidence: 0.90
```
