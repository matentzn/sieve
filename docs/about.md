# About SIEVE

SIEVE (Scientific Evidence Evaluation & Verification Environment) is an open-source framework for curating and managing evidence that supports ontological assertions.

## Motivation

Ontology development and maintenance requires careful evaluation of evidence supporting classification decisions. For example, when asserting that "asthma is a subclass of respiratory system disorder," curators need to:

- Gather supporting evidence from literature, other ontologies, and expert review
- Evaluate contradicting evidence and edge cases
- Document the rationale for decisions
- Track who made decisions and when
- Export decisions in formats usable by ontology workflows

SIEVE provides a structured framework for this entire process.

## Features

- **Multi-source Evidence**: Supports literature, cross-ontology concordance, expert review, and computational evidence
- **Evidence Scoring**: Calculates Net Evidence Ratio to summarize supporting vs. contradicting evidence
- **Web Interface**: Streamlit-based UI for interactive curation
- **ORCID Authentication**: Tracks curator identity via ORCID OAuth
- **RDF Export**: Generates OWL axiom annotations for ontology integration
- **Schema Validation**: LinkML-based validation ensures data quality
- **Audit Trail**: Records all decisions with timestamps and rationale

## Use Cases

- Disease ontology curation (Mondo, DOID)
- Cross-ontology alignment validation
- Evidence-based ontology quality assurance
- Collaborative multi-curator review workflows
- AI-assisted evidence aggregation and synthesis

## Technology

SIEVE is built with:

- **Python 3.10+** for the core framework
- **LinkML** for data modeling
- **DuckDB** for embedded database
- **Streamlit** for web interface
- **RDFLib** for RDF generation
- **Typer** for CLI

## Contributing

SIEVE is open source and welcomes contributions. See the [GitHub repository](https://github.com/matentzn/sieve) for:

- Issue tracking
- Pull requests
- Development guidelines

## License

See the repository for license information.
