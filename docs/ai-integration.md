# Authoring Packets as an AI Agent

This page is for AI agents (LLMs, autonomous pipelines) that **produce evidence** for
SIEVE. It covers only the AI-specific parts: what an agent records, and which checks
it must report honestly.

It does not re-teach the data model. Read these first:

- [SIEVE in Plain Terms](primer.md): claims, items, lines, decisions.
- [Data Model](data-model.md): every class and field.

## What you produce

An agent's output is one `EvidencePacket` per claim, in the profile shape (camelCase,
`id` and `type` on every entity). An agent typically contributes three things:

- **evidence items it created**: a `TextPassage` with the verbatim quote it
  extracted, plus the `Publication` / `WebPage` / `GuidelineDocument` it came from;
- **evidence lines**: its interpretation of those items, each with an
  `InterpretationActivity` of `methodType: LLM_JUDGEMENT`;
- **groundings**: `ResolutionChain`s recording how mentions in the passage were
  resolved to Mondo, HGNC or other ids, step by step.

An agent does **not** write `assertionDecisions` and does not set the inclusion score.
Decisions are made by a person, or by a policy runner acting under a human-approved
`DecisionPolicy`. Leave `reviewState: NOT_VERIFIED`, and set
`proposingChannel: AI_AGENT` when the agent proposed the claim.

## What the profile asks of AI evidence

| Where | Field | What to record |
|---|---|---|
| `TextPassage` | `statementText` | The quote, verbatim. |
| | `reportedIn`, `documentVersion`, `textLocation` | Which document and version, and where (section, character offsets). |
| | `quoteVerification` | `VERIFIED` only if a machine check found the quote in the source; otherwise `NOT_CHECKED` or `FAILED`. |
| | `contributions` | The extraction act: `contributor`, `role: EXTRACTOR`, `date`, `specifiedBy` (prompt or workflow version), `runId`. Required. |
| `InterpretationActivity` | `methodType` | `LLM_JUDGEMENT`. |
| | `specifiedBy` | The prompt or workflow version. Required for AI lines. |
| | `readCoverage`, `accessStatus` | How much of the document was read (`TITLE_ONLY`, `ABSTRACT_ONLY`, `SECTIONS`, `FULL_TEXT`) and whether it was open. Required on document-based lines. |
| | `identifierVerified`, `groundingChecked` | Whether the cited id resolves and is about the topic, and whether the entities map to the claim's actual terms. |
| | `soughtDisputingEvidence` | Whether the search looked for evidence against the claim. |
| | `reasoningTrace` | A link to the trace. The trace itself is not stored. |
| `SieveEvidenceLine` | `confidence`, `confidenceBasis` | The probability the evidence was read and linked correctly, and its basis (usually `PRIOR` for a pinned model version, `MEASURED` if a scorer evaluated this input). A confidence without a basis fails validation. |
| | `dataQualityFlags` | Flag known failures (`QUOTE_NOT_FOUND`, `IDENTIFIER_UNRESOLVED`, `MISGROUNDED`, `SUSPECTED_HALLUCINATION`). |
| `SieveAgent` (registry) | `softwareVersion`, `modelName`, `trustLevels` | The agent's version and model. Trust is maintained by the registry, from the agent's record of accepted and invalidated lines. |

Confidence is data quality, not evidence strength. Put your read of how strongly the
evidence bears on the claim in `scoreOfEvidenceProvided`, and your read of whether you
extracted and grounded it correctly in `confidence`.

## An example

Adapted from `tests/data/profile/valid/c007_cf_cftr_panel.yaml` (the passage text is
illustrative):

```yaml
id: sieve:pkt/MONDO_0009061-gene-HGNC_1884
type: EvidencePacket
version: "2026-10-10"
statement:
  id: sieve:st/MONDO_0009061-gene-HGNC_1884
  type: DiseaseAttributeStatement
  subject: MONDO:0009061              # cystic fibrosis
  predicate: {code: RO:0004003, label: has material basis in germline mutation in}
  object: HGNC:1884                   # CFTR
  reviewState: NOT_VERIFIED
  proposingChannel: AI_AGENT
  hasEvidenceLines:
    - id: sieve:el/cf-passage
      type: SieveEvidenceLine
      hasEvidenceItems: [sieve:tp/pmid-20301428-1]
      directionOfEvidenceProvided: supports
      scoreOfEvidenceProvided: 0.8
      confidence: 0.85
      confidenceBasis: PRIOR
      contributions:
        - id: sieve:act/cf-passage
          type: InterpretationActivity
          contributor: sieve:agent/mondo-ai-extractor
          role: INTERPRETER
          date: "2026-10-10"
          methodType: LLM_JUDGEMENT
          specifiedBy: [sieve:method/evidence-extraction-prompt]
          readCoverage: FULL_TEXT
          accessStatus: OPEN_ACCESS
          identifierVerified: VERIFIED
          groundingChecked: VERIFIED
          soughtDisputingEvidence: true
          runId: mondo-ai-evidence-2026-10-10-r7
textPassages:
  - id: sieve:tp/pmid-20301428-1
    type: TextPassage
    statementText: "Illustrative passage: cystic fibrosis is caused by pathogenic variants in CFTR."
    reportedIn: [PMID:20301428]
    documentVersion: "2025-01"
    textLocation: {section: Molecular Genetics, charStart: 1200, charEnd: 1278}
    quoteVerification: NOT_CHECKED    # VERIFIED only after a machine check
    contributions:
      - id: sieve:act/tp-extraction
        type: SieveContribution
        contributor: sieve:agent/mondo-ai-extractor
        role: EXTRACTOR
        date: "2026-10-10"
        specifiedBy: [sieve:method/evidence-extraction-prompt]
        runId: mondo-ai-evidence-2026-10-10-r7
publications:
  - id: PMID:20301428
    type: Publication
    pmid: "20301428"
    resource: infores:pubmed
    generationContext:
      - {code: "PT:review", label: Review}
```

The full test file adds the resolution chain for "CFTR" (an LLM extraction step, then
a lexical grounding step to `HGNC:1884`), an OMIM concordance line, a reviewer's
`LineStatusChange` accepting the AI line unchanged, and a panel's decision.

## What happens to your lines

A reviewer either accepts a line unchanged, or invalidates it, or writes a corrected
line that supersedes it. Your line is never edited. Each outcome is recorded as a
`LineStatusChange` and counts towards your agent's trust level.

## Validating your output

```bash
uv run linkml-validate -s schema/sieve.yaml -C EvidencePacket my_packet.yaml
```

```python
import yaml
from sieve.profile_checks import check_packet

issues = check_packet(yaml.safe_load(open("my_packet.yaml")))
errors = [i for i in issues if i.severity == "ERROR"]
```

Quote dates in YAML for linkml-validate. `check_packet` catches what JSON Schema cannot,
including a document-based line without `readCoverage` / `accessStatus`, an AI line
without `specifiedBy`, a predicate outside the claim type's value set, evidence the
claim type does not permit, and references to items that are not in the packet. Fix
every ERROR before handing a packet off.

## DO / DON'T

**DO**

- Quote source text **verbatim**, with its location and the document version.
- Cite real, resolvable identifiers, and say whether you checked them.
- Add a `disputes` line when the evidence cuts against the claim.
- Record how much of the document you actually read.
- State a confidence only with its basis.

**DON'T**

- Don't fabricate references, PMIDs, quotes or concordances.
- Don't set `quoteVerification: VERIFIED` or `identifierVerified: VERIFIED` without a
  machine check.
- Don't write `assertionDecisions`, `reviewState: VERIFIED` or the statement `score`.
- Don't fold data quality into strength: a shaky extraction gets a low `confidence`,
  not a low `scoreOfEvidenceProvided`.
- Don't use the pre-profile shape (`status`, `has_evidence_lines`, `SieveDocument`,
  `ComputationalResult`, items inlined in lines).
