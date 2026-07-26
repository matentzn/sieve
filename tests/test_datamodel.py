"""The generated datamodel imports and constructs a minimal packet."""

from sieve.datamodel import (
    ConcordanceItem,
    CurationDecision,
    EvidencePacket,
    SieveStatement,
)


def test_construct_minimal_packet():
    # SEPIO Entity requires id + type on every entity (inherited).
    packet = EvidencePacket(
        id="sieve:pkt_0001",
        statement=SieveStatement(
            id="stmt_1",
            type="SieveStatement",
            subject="MONDO:0004979",
            object="MONDO:0005275",
        ),
        status="UNREVIEWED",
    )
    assert packet.id == "sieve:pkt_0001"
    assert packet.status == "UNREVIEWED"


def test_curated_evidence_item_accepts_rating_and_eco():
    item = ConcordanceItem(
        id="ev_1",
        type="ConcordanceItem",
        rating="ACCEPTED",
        eco_code="ECO:0000269",
        sourceName="DOID",
    )
    assert item.rating == "ACCEPTED"
    assert item.eco_code == "ECO:0000269"


def test_curation_decision_constructs():
    d = CurationDecision(
        id="dec_1",
        packet_id="sieve:pkt_0001",
        curator="orcid:0000-0002-0000-0000",
        decision="ACCEPT",
        decided_at="2026-07-26T00:00:00",
    )
    assert d.decision == "ACCEPT"
