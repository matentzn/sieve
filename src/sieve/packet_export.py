"""Export EvidencePackets to RDF (OWL axiom annotations) and YAML."""

import sys
from pathlib import Path
from typing import Optional

import curies
import yaml
from rdflib import OWL, RDF, RDFS, BNode, Graph, Literal, Namespace, URIRef

from sieve.datamodel import EvidencePacket

# Namespaces
SEPIO = Namespace("http://purl.obolibrary.org/obo/SEPIO_")
OBOINOWL = Namespace("http://www.geneontology.org/formats/oboInOwl#")
ORCID = Namespace("https://orcid.org/")
IAO = Namespace("http://purl.obolibrary.org/obo/IAO_")

VALID_STATUSES = {"ACCEPTED", "REJECTED", "CONTROVERSIAL"}


def get_obo_converter() -> curies.Converter:
    """Get the OBO converter for CURIE expansion."""
    return curies.get_obo_converter()


def expand_curie(curie: Optional[str], converter: curies.Converter) -> Optional[URIRef]:
    """Expand a CURIE (or URI) to a full URIRef, or None if it cannot be expanded."""
    if not curie:
        return None
    if curie.startswith("orcid:"):
        return URIRef(f"https://orcid.org/{curie.replace('orcid:', '')}")
    if curie.startswith("rdfs:"):
        return RDFS[curie.replace("rdfs:", "")]
    if curie.startswith("owl:"):
        return OWL[curie.replace("owl:", "")]
    if curie.startswith("http://") or curie.startswith("https://"):
        return URIRef(curie)
    expanded = converter.expand(curie)
    if expanded:
        return URIRef(expanded)
    if ":" in curie:
        prefix, local = curie.split(":", 1)
        return URIRef(f"http://purl.obolibrary.org/obo/{prefix}_{local}")
    return None


def _packet_uri(packet_id: Optional[str]) -> Optional[URIRef]:
    if not packet_id:
        return None
    if packet_id.startswith("http://") or packet_id.startswith("https://"):
        return URIRef(packet_id)
    return URIRef(f"http://purl.org/np/{packet_id}")


def _accepted_item_sources(packet: EvidencePacket) -> list[str]:
    """CURIE/identifier sources from ACCEPTED items on supporting lines."""
    sources: list[str] = []
    for line in packet.hasEvidenceLines or []:
        if (line.directionOfEvidenceProvided or "").lower() != "supports":
            continue
        for item in line.hasEvidenceItems or []:
            if getattr(item, "rating", None) != "ACCEPTED":
                continue
            for attr in ("pmid", "doi", "sourceId", "sourceSubject"):
                val = getattr(item, attr, None)
                if val:
                    sources.append(str(val))
            contributor = getattr(item, "contributor", None)
            if contributor is not None and getattr(contributor, "id", None):
                sources.append(str(contributor.id))
    return sources


def packet_to_rdf(packet: EvidencePacket, graph: Optional[Graph] = None) -> Graph:
    """Convert an EvidencePacket to an owl:Axiom annotation in an RDF graph.

    Only ACCEPTED/REJECTED/CONTROVERSIAL packets produce triples; others are
    skipped with a warning (an empty graph is still returned).
    """
    if graph is None:
        graph = Graph()
        for prefix, ns in (
            ("owl", OWL), ("rdfs", RDFS), ("SEPIO", SEPIO),
            ("oboInOwl", OBOINOWL), ("orcid", ORCID), ("IAO", IAO),
        ):
            graph.bind(prefix, ns)

    status = str(packet.status) if packet.status else None
    if status not in VALID_STATUSES:
        print(
            f"WARNING: skipping packet '{packet.id}' - status '{status}' is not "
            "one of ACCEPTED/REJECTED/CONTROVERSIAL.",
            file=sys.stderr,
        )
        return graph

    converter = get_obo_converter()
    stmt = packet.statement
    predicate_code = getattr(stmt.predicate, "code", None) if stmt and stmt.predicate else None
    subject_uri = expand_curie(getattr(stmt, "subject", None), converter)
    predicate_uri = expand_curie(predicate_code or "rdfs:subClassOf", converter)
    object_uri = expand_curie(getattr(stmt, "object", None), converter)
    if subject_uri is None or predicate_uri is None or object_uri is None:
        return graph

    steward = None
    if packet.curated_by and getattr(packet.curated_by, "contributor", None):
        steward = getattr(packet.curated_by.contributor, "id", None)
    steward_uri = expand_curie(steward, converter)
    packet_uri = _packet_uri(str(packet.id) if packet.id else None)

    axiom = BNode()
    graph.add((axiom, RDF.type, OWL.Axiom))
    graph.add((axiom, OWL.annotatedSource, subject_uri))
    graph.add((axiom, OWL.annotatedProperty, predicate_uri))
    graph.add((axiom, OWL.annotatedTarget, object_uri))
    if packet_uri:
        graph.add((axiom, SEPIO["0000124"], packet_uri))

    if status == "ACCEPTED":
        if steward_uri:
            graph.add((axiom, OBOINOWL.source, steward_uri))
        for src in _accepted_item_sources(packet):
            graph.add((axiom, OBOINOWL.source, Literal(src)))
    elif status == "REJECTED":
        if packet_uri:
            graph.add((axiom, IAO["0000233"], packet_uri))
        if steward_uri:
            graph.add((axiom, OBOINOWL.source, steward_uri))
    elif status == "CONTROVERSIAL":
        graph.add((axiom, RDFS.comment, Literal("CONTROVERSIAL: See evidence packet for discussion")))
        if packet_uri:
            graph.add((axiom, IAO["0000233"], packet_uri))
        if steward_uri:
            graph.add((axiom, OBOINOWL.source, steward_uri))

    return graph


def export_packets_to_rdf(
    packets: list[EvidencePacket],
    output_path: Optional[Path] = None,
    format: str = "turtle",
) -> str:
    """Export a list of EvidencePackets to a single RDF document."""
    graph = Graph()
    for prefix, ns in (
        ("owl", OWL), ("rdfs", RDFS), ("SEPIO", SEPIO),
        ("oboInOwl", OBOINOWL), ("orcid", ORCID), ("IAO", IAO),
    ):
        graph.bind(prefix, ns)
    for packet in packets:
        packet_to_rdf(packet, graph)
    rdf_str = graph.serialize(format=format)
    if output_path:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(rdf_str, encoding="utf-8")
    return rdf_str
