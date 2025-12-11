"""Export accepted assertions to RDF."""

from datetime import datetime
from pathlib import Path

from rdflib import BNode, Graph, Literal, Namespace, URIRef
from rdflib.namespace import PROV, RDF, XSD

from curation_app.db import CurationDatabase

# Namespaces
CURA = Namespace("https://w3id.org/curation-app/")
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


def export_accepted_records(
    db: CurationDatabase,
    output_path: Path,
    format: str = "turtle",
    include_provenance: bool = True,
) -> Path:
    """
    Export all accepted records to RDF.

    Args:
        db: Database connection
        output_path: Directory for output file
        format: RDF serialization format (turtle, xml, json-ld, n3)
        include_provenance: Whether to include curation provenance

    Returns:
        Path to generated file
    """
    g = Graph()

    # Bind prefixes
    g.bind("cura", CURA)
    g.bind("prov", PROV)
    g.bind("orcid", ORCID)

    accepted_records = db.get_records_by_status("ACCEPTED")

    for record in accepted_records:
        # Create the main assertion triple
        subject = URIRef(expand_curie(record["assertion_subject_id"]))
        predicate = URIRef(expand_curie(record["assertion_predicate"]))
        obj = URIRef(expand_curie(record["assertion_object_id"]))

        g.add((subject, predicate, obj))

        if include_provenance:
            # Get decision info
            decisions = db.get_decisions_for_record(record["id"])
            if decisions:
                decision = decisions[0]  # Most recent

                # Create provenance node
                decision_uri = CURA[f"decision/{record['id']}"]
                g.add((decision_uri, RDF.type, CURA.CurationDecision))

                # Link to assertion via reification
                assertion_node = BNode()
                g.add((decision_uri, CURA.approvedAssertion, assertion_node))
                g.add((assertion_node, RDF.subject, subject))
                g.add((assertion_node, RDF.predicate, predicate))
                g.add((assertion_node, RDF.object, obj))

                # Add decision metadata
                if decision.get("curator_orcid"):
                    g.add(
                        (
                            decision_uri,
                            PROV.wasAttributedTo,
                            URIRef(expand_curie(decision["curator_orcid"])),
                        )
                    )

                if decision.get("decided_at"):
                    g.add(
                        (
                            decision_uri,
                            PROV.generatedAtTime,
                            Literal(decision["decided_at"], datatype=XSD.dateTime),
                        )
                    )

                # Link to source artifact
                if record.get("source_artifact_uri"):
                    g.add(
                        (
                            decision_uri,
                            PROV.wasDerivedFrom,
                            URIRef(record["source_artifact_uri"]),
                        )
                    )

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
    g.bind("cura", CURA)
    g.bind("prov", PROV)

    subject = URIRef(expand_curie(record["assertion_subject_id"]))
    predicate = URIRef(expand_curie(record["assertion_predicate"]))
    obj = URIRef(expand_curie(record["assertion_object_id"]))

    g.add((subject, predicate, obj))

    return g.serialize(format="turtle")
