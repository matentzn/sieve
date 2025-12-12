"""Export accepted assertions to RDF."""

from datetime import datetime
from pathlib import Path

from rdflib import BNode, Graph, Literal, Namespace, URIRef
from rdflib.namespace import OWL, RDF, RDFS, XSD

from sieve.db import CurationDatabase

# Namespaces
OBOINOWL = Namespace("http://www.geneontology.org/formats/oboInOwl#")
SEPIO = Namespace("http://purl.obolibrary.org/obo/SEPIO_")
ORCID = Namespace("https://orcid.org/")


def expand_curie(curie: str) -> str:
    """Expand common CURIEs to full URIs."""
    prefix_map = {
        "MONDO": "http://purl.obolibrary.org/obo/MONDO_",
        "DOID": "http://purl.obolibrary.org/obo/DOID_",
        "HP": "http://purl.obolibrary.org/obo/HP_",
        "GO": "http://purl.obolibrary.org/obo/GO_",
        "CHEBI": "http://purl.obolibrary.org/obo/CHEBI_",
        "ECO": "http://purl.obolibrary.org/obo/ECO_",
        "orcid": "https://orcid.org/",
        "PMID": "https://pubmed.ncbi.nlm.nih.gov/",
        "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
        "owl": "http://www.w3.org/2002/07/owl#",
        "skos": "http://www.w3.org/2004/02/skos/core#",
    }

    if "://" in curie:
        return curie  # Already a URI

    if ":" in curie:
        prefix, local = curie.split(":", 1)
        if prefix in prefix_map:
            return prefix_map[prefix] + local

    return curie


def create_owl_axiom_annotation(
    g: Graph,
    subject: URIRef,
    predicate: URIRef,
    obj: URIRef,
    curator_orcid: str | None = None,
    evidence_id: str | None = None,
) -> BNode:
    """Create an OWL axiom annotation for a triple.

    This creates standard OWL2 reification using owl:Axiom with
    owl:annotatedSource, owl:annotatedProperty, owl:annotatedTarget.

    Args:
        g: RDF graph to add triples to
        subject: The subject of the annotated triple
        predicate: The predicate of the annotated triple
        obj: The object of the annotated triple
        curator_orcid: Optional ORCID of the curator (used as oboInOwl:source)
        evidence_id: Optional ID of the evidence packet (used as SEPIO:0000124)

    Returns:
        The BNode representing the axiom annotation
    """
    axiom = BNode()
    g.add((axiom, RDF.type, OWL.Axiom))
    g.add((axiom, OWL.annotatedSource, subject))
    g.add((axiom, OWL.annotatedProperty, predicate))
    g.add((axiom, OWL.annotatedTarget, obj))

    if curator_orcid:
        # Normalize ORCID to full URI
        if curator_orcid.startswith("orcid:"):
            curator_orcid = curator_orcid[6:]
        curator_uri = ORCID[curator_orcid]
        g.add((axiom, OBOINOWL.source, curator_uri))

    if evidence_id:
        evidence_uri = URIRef(evidence_id)
        # SEPIO:0000124 = has_evidence
        g.add((axiom, SEPIO["0000124"], evidence_uri))

    return axiom


def export_accepted_records(
    db: CurationDatabase,
    output_path: Path,
    format: str = "turtle",
    include_provenance: bool = True,
) -> Path:
    """Export all accepted records to RDF with OWL axiom annotations.

    Args:
        db: Database connection
        output_path: Directory for output file
        format: RDF serialization format (turtle, xml, json-ld, n3)
        include_provenance: Whether to include curation provenance as axiom annotations

    Returns:
        Path to generated file
    """
    g = Graph()

    # Bind prefixes for cleaner output
    g.bind("owl", OWL)
    g.bind("rdfs", RDFS)
    g.bind("oboInOwl", OBOINOWL)
    g.bind("SEPIO", SEPIO)
    g.bind("orcid", ORCID)

    accepted_records = db.get_records_by_status("ACCEPTED")

    for record in accepted_records:
        # Create URIs for the assertion
        subject = URIRef(expand_curie(record["assertion_subject_id"]))
        predicate = URIRef(expand_curie(record["assertion_predicate"]))
        obj = URIRef(expand_curie(record["assertion_object_id"]))

        if include_provenance:
            # Get decision info for curator ORCID
            decisions = db.get_decisions_for_record(record["id"])
            curator_orcid = None
            if decisions:
                decision = decisions[0]  # Most recent
                curator_orcid = decision.get("curator_orcid")

            # Use record ID directly as evidence packet reference
            evidence_id = record.get("id")

            # Create OWL axiom annotation (no direct triple needed)
            create_owl_axiom_annotation(
                g=g,
                subject=subject,
                predicate=predicate,
                obj=obj,
                curator_orcid=curator_orcid,
                evidence_id=evidence_id,
            )
        else:
            # Without provenance, just add the direct triple
            g.add((subject, predicate, obj))

    # Generate output filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    ext_map = {"turtle": "ttl", "xml": "rdf", "json-ld": "jsonld", "n3": "n3"}
    ext = ext_map.get(format, "ttl")

    output_dir = Path(output_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / f"export_{timestamp}.{ext}"

    g.serialize(destination=str(output_file), format=format)

    return output_file


def export_record_as_rdf(record: dict, db: CurationDatabase) -> str:
    """Export a single record to Turtle string."""
    g = Graph()
    g.bind("owl", OWL)
    g.bind("rdfs", RDFS)
    g.bind("oboInOwl", OBOINOWL)
    g.bind("SEPIO", SEPIO)
    g.bind("orcid", ORCID)

    subject = URIRef(expand_curie(record["assertion_subject_id"]))
    predicate = URIRef(expand_curie(record["assertion_predicate"]))
    obj = URIRef(expand_curie(record["assertion_object_id"]))

    g.add((subject, predicate, obj))

    return g.serialize(format="turtle")
