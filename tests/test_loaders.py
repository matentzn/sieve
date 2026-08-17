"""Evidence items deserialize to their concrete subclasses."""

from sieve.datamodel import ConcordanceItem, SieveDocument
from sieve.datamodel.loaders import packet_from_dict


def test_items_dispatch_to_subclasses():
    data = {
        "id": "sieve:pkt_1",
        "status": "UNREVIEWED",
        "statement": {"id": "stmt_1", "type": "SieveStatement", "subject": "MONDO:1", "object": "MONDO:2"},
        "has_evidence_lines": [
            {
                "id": "line_1",
                "type": "SieveEvidenceLine",
                "direction_of_evidence_provided": "supports",
                "has_evidence_items": [
                    {"id": "ev_1", "type": "ConcordanceItem", "source_name": "DOID", "rating": "ACCEPTED"},
                    {"id": "ev_2", "type": "SieveDocument", "quote": "…", "pmid": "12345678"},
                ],
            }
        ],
    }
    packet = packet_from_dict(data)
    items = packet.has_evidence_lines[0].has_evidence_items
    assert isinstance(items[0], ConcordanceItem)
    assert items[0].rating == "ACCEPTED"
    assert isinstance(items[1], SieveDocument)
    assert items[1].quote == "…"
