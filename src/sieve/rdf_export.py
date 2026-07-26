"""Export evidence packets to RDF (OWL axiom annotations)."""

import sys
from pathlib import Path
from typing import Iterator

import curies
import yaml
from rdflib import OWL, RDF, RDFS, BNode, Graph, Literal, Namespace, URIRef

# Define namespaces
SEPIO = Namespace("http://purl.obolibrary.org/obo/SEPIO_")
OBOINOWL = Namespace("http://www.geneontology.org/formats/oboInOwl#")
ORCID = Namespace("https://orcid.org/")
OBO = Namespace("http://purl.obolibrary.org/obo/")
IAO = Namespace("http://purl.obolibrary.org/obo/IAO_")

# Valid statuses for export
VALID_STATUSES = {"ACCEPTED", "REJECTED", "CONTROVERSIAL"}


def get_obo_converter() -> curies.Converter:
    """Get the OBO converter for CURIE expansion."""
    return curies.get_obo_converter()


def expand_curie(curie: str, converter: curies.Converter) -> URIRef | None:
    """Expand a CURIE to a full URI.

    Args:
        curie: The CURIE to expand (e.g., "MONDO:0005015")
        converter: The curies converter

    Returns:
        URIRef or None if expansion fails
    """
    if not curie:
        return None

    # Handle orcid: prefix specially
    if curie.startswith("orcid:"):
        orcid_id = curie.replace("orcid:", "")
        return URIRef(f"https://orcid.org/{orcid_id}")

    # Handle rdfs: prefix
    if curie.startswith("rdfs:"):
        local = curie.replace("rdfs:", "")
        return RDFS[local]

    # Handle owl: prefix
    if curie.startswith("owl:"):
        local = curie.replace("owl:", "")
        return OWL[local]

    # Handle http/https URIs directly
    if curie.startswith("http://") or curie.startswith("https://"):
        return URIRef(curie)

    # Try to expand using the converter
    expanded = converter.expand(curie)
    if expanded:
        return URIRef(expanded)

    # Fallback: try OBO-style expansion for common prefixes
    if ":" in curie:
        prefix, local = curie.split(":", 1)
        # OBO convention: PREFIX:1234 -> http://purl.obolibrary.org/obo/PREFIX_1234
        return URIRef(f"http://purl.obolibrary.org/obo/{prefix}_{local}")

    return None


def packet_to_rdf(packet: dict, graph: Graph | None = None, source_path: Path | None = None) -> Graph | None:
    """Convert an evidence packet to RDF as an OWL axiom annotation.

    Creates an owl:Axiom annotation with:
    - owl:annotatedSource: the subject of the assertion
    - owl:annotatedProperty: the predicate (typically rdfs:subClassOf)
    - owl:annotatedTarget: the object of the assertion
    - SEPIO:0000124: the evidence packet ID (nanopub reference)
    - Status-specific property based on packet status:
      - ACCEPTED: oboInOwl:source (evidence steward ORCID)
      - REJECTED: IAO:0000233 (term tracker item) with rejection note
      - CONTROVERSIAL: rdfs:comment with controversy note

    Args:
        packet: The evidence packet dict (from YAML)
        graph: Optional existing graph to add to
        source_path: Optional path to the source file (for warning messages)

    Returns:
        The RDF graph with the axiom annotation, or None if packet has no valid status
    """
    # Check for valid status - skip packets without status
    status = packet.get("status")
    if not status:
        source_info = f" ({source_path})" if source_path else ""
        packet_id = packet.get("id", "unknown")
        print(
            f"WARNING: Skipping evidence packet '{packet_id}'{source_info} - "
            f"no status field. Only ACCEPTED, REJECTED, or CONTROVERSIAL packets can be exported.",
            file=sys.stderr,
        )
        return graph

    if status not in VALID_STATUSES:
        source_info = f" ({source_path})" if source_path else ""
        packet_id = packet.get("id", "unknown")
        print(
            f"WARNING: Skipping evidence packet '{packet_id}'{source_info} - "
            f"invalid status '{status}'. Only ACCEPTED, REJECTED, or CONTROVERSIAL packets can be exported.",
            file=sys.stderr,
        )
        return graph

    if graph is None:
        graph = Graph()
        # Bind common prefixes
        graph.bind("owl", OWL)
        graph.bind("rdfs", RDFS)
        graph.bind("SEPIO", SEPIO)
        graph.bind("oboInOwl", OBOINOWL)
        graph.bind("orcid", ORCID)
        graph.bind("IAO", IAO)

    converter = get_obo_converter()

    # Get assertion components
    assertion = packet.get("assertion", {})
    subject_id = assertion.get("subject_id")
    predicate = assertion.get("predicate", "rdfs:subClassOf")
    object_id = assertion.get("object_id")

    # Expand CURIEs
    subject_uri = expand_curie(subject_id, converter)
    predicate_uri = expand_curie(predicate, converter)
    object_uri = expand_curie(object_id, converter)

    if subject_uri is None or predicate_uri is None or object_uri is None:
        return graph

    # Get packet ID and evidence steward
    packet_id = packet.get("id")
    evidence_steward = packet.get("evidence_steward")

    packet_uri = None
    if packet_id:
        if packet_id.startswith("http://") or packet_id.startswith("https://"):
            packet_uri = URIRef(packet_id)
        else:
            # Assume it's a nanopub-style ID
            packet_uri = URIRef(f"http://purl.org/np/{packet_id}")

    steward_uri = None
    if evidence_steward:
        steward_uri = expand_curie(evidence_steward, converter)

    # Create the axiom annotation (blank node)
    axiom = BNode()
    graph.add((axiom, RDF.type, OWL.Axiom))
    graph.add((axiom, OWL.annotatedSource, subject_uri))
    graph.add((axiom, OWL.annotatedProperty, predicate_uri))
    graph.add((axiom, OWL.annotatedTarget, object_uri))

    # Add evidence packet reference
    if packet_uri:
        graph.add((axiom, SEPIO["0000124"], packet_uri))

    # Add status-specific annotations
    if status == "ACCEPTED":
        # Add evidence steward as oboInOwl:source
        if steward_uri:
            graph.add((axiom, OBOINOWL.source, steward_uri))

        # Add additional sources from accepted supporting evidence
        # For evidence with direction=SUPPORTS and rating=ACCEPTED,
        # add relevant fields as CURIE string literals
        for evidence in packet.get("evidence", []):
            if (
                evidence.get("direction") == "SUPPORTS"
                and evidence.get("rating") == "ACCEPTED"
            ):
                ev_type = evidence.get("evidence_type")

                # Add publication_id (from CONCORDANCE or LITERATURE)
                if evidence.get("publication_id"):
                    graph.add((axiom, OBOINOWL.source, Literal(evidence["publication_id"])))

                # Add source_subject_id (from CONCORDANCE)
                if ev_type == "CONCORDANCE" and evidence.get("source_subject_id"):
                    graph.add((axiom, OBOINOWL.source, Literal(evidence["source_subject_id"])))

                # Add reviewer_orcid (from CONCORDANCE or EXPERT_REVIEW)
                if evidence.get("reviewer_orcid"):
                    graph.add((axiom, OBOINOWL.source, Literal(evidence["reviewer_orcid"])))

    elif status == "REJECTED":
        # Use IAO:0000233 (term tracker item) for rejected assertions
        # This indicates there's a tracker item explaining why this was rejected
        if packet_uri:
            graph.add((axiom, IAO["0000233"], packet_uri))
        # Add steward who rejected it
        if steward_uri:
            graph.add((axiom, OBOINOWL.source, steward_uri))

    elif status == "CONTROVERSIAL":
        # Use rdfs:comment for controversial assertions
        graph.add((axiom, RDFS.comment, Literal("CONTROVERSIAL: See evidence packet for discussion")))
        if packet_uri:
            graph.add((axiom, IAO["0000233"], packet_uri))
        # Add steward who marked it controversial
        if steward_uri:
            graph.add((axiom, OBOINOWL.source, steward_uri))

    return graph


def load_packet(path: Path) -> dict:
    """Load an evidence packet from a YAML file.

    Args:
        path: Path to the YAML file

    Returns:
        The parsed packet dict
    """
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def iter_packets(path: Path) -> Iterator[tuple[Path, dict]]:
    """Iterate over evidence packets from a file or directory.

    Args:
        path: Path to a YAML file or directory containing YAML files

    Yields:
        Tuples of (file_path, packet_dict)
    """
    path = Path(path)

    if path.is_file():
        yield path, load_packet(path)
    elif path.is_dir():
        for yaml_file in sorted(path.glob("**/*.yaml")):
            yield yaml_file, load_packet(yaml_file)
        for yml_file in sorted(path.glob("**/*.yml")):
            yield yml_file, load_packet(yml_file)


def export_to_rdf(
    input_path: Path,
    output_path: Path | None = None,
    format: str = "turtle",
) -> str:
    """Export evidence packet(s) to RDF.

    Only packets with valid status (ACCEPTED, REJECTED, CONTROVERSIAL) are exported.
    Packets without a status or with UNREVIEWED status will be skipped with a warning.

    Args:
        input_path: Path to a YAML file or directory
        output_path: Optional output path. If None, returns the serialized RDF
        format: RDF serialization format (turtle, xml, n3, nt)

    Returns:
        The serialized RDF string
    """
    graph = Graph()
    graph.bind("owl", OWL)
    graph.bind("rdfs", RDFS)
    graph.bind("SEPIO", SEPIO)
    graph.bind("oboInOwl", OBOINOWL)
    graph.bind("orcid", ORCID)
    graph.bind("IAO", IAO)

    for source_path, packet in iter_packets(input_path):
        packet_to_rdf(packet, graph, source_path=source_path)

    # Serialize
    rdf_str = graph.serialize(format=format)

    if output_path:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(rdf_str)

    return rdf_str
