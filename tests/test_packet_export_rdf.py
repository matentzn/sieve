from pathlib import Path

from rdflib import OWL, URIRef

from sieve.datamodel.loaders import load_packet
from sieve.datamodel import (
    ConcordanceItem,
    EvidencePacket,
    SieveEvidenceLine,
    SieveStatement,
)
from sieve.packet_export import packet_to_rdf

EX = Path(__file__).parent.parent / "inbox" / "examples" / "asthma_subclass.sepio.yaml"


def test_accepted_packet_emits_axiom_with_spo():
    graph = packet_to_rdf(load_packet(EX))
    axioms = list(graph.subjects(predicate=OWL.annotatedSource))
    assert len(axioms) == 1
    subjects = set(graph.objects(predicate=OWL.annotatedSource))
    assert URIRef("http://purl.obolibrary.org/obo/MONDO_0004979") in subjects


def test_accepted_sources_only_from_accepted_supporting_items():
    graph = packet_to_rdf(load_packet(EX))
    oio_source = URIRef("http://www.geneontology.org/formats/oboInOwl#source")
    sources = {str(o) for o in graph.objects(predicate=oio_source)}
    # ACCEPTED supporting document PMID is included...
    assert "28884740" in sources
    # ...the DOID concordance is on a DISPUTES line (rating REJECTED) and excluded.
    assert "DOID:2841" not in sources


def test_unreviewed_packet_emits_nothing():
    packet = EvidencePacket(
        id="p_unrev",
        status="UNREVIEWED",
        statement=SieveStatement(id="s", type="SieveStatement", subject="MONDO:1", object="MONDO:2"),
        has_evidence_lines=[
            SieveEvidenceLine(
                id="l",
                type="SieveEvidenceLine",
                direction_of_evidence_provided="supports",
                has_evidence_items=[ConcordanceItem(id="e", type="ConcordanceItem", source_name="X")],
            )
        ],
    )
    graph = packet_to_rdf(packet)
    assert len(list(graph)) == 0
