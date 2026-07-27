from sieve.datamodel import (
    ConcordanceItem,
    CurationDecision,
    EvidencePacket,
    SieveEvidenceLine,
    SieveStatement,
)
from sieve.store import PacketStore


def _packet():
    return EvidencePacket(
        id="sieve:pkt_1",
        status="UNREVIEWED",
        statement=SieveStatement(
            id="s1",
            type="SieveStatement",
            subject="MONDO:0004979",
            object="MONDO:0005275",
        ),
        hasEvidenceLines=[
            SieveEvidenceLine(
                id="l1",
                type="SieveEvidenceLine",
                directionOfEvidenceProvided="supports",
                scoreOfEvidenceProvided=0.9,
                hasEvidenceItems=[ConcordanceItem(id="e1", type="ConcordanceItem", sourceName="DOID")],
            )
        ],
    )


def test_insert_and_get_roundtrip():
    store = PacketStore(":memory:")
    store.insert_packet(_packet())
    got = store.get_packet("sieve:pkt_1")
    assert got is not None
    assert got.statement.subject == "MONDO:0004979"
    item = got.hasEvidenceLines[0].hasEvidenceItems[0]
    assert isinstance(item, ConcordanceItem)
    # subclass fields must survive the JSON round-trip (serialize_as_any)
    assert item.sourceName == "DOID"


def test_promoted_columns_and_score():
    store = PacketStore(":memory:")
    store.insert_packet(_packet())
    row = store.list_packets()[0]
    assert row["subject_id"] == "MONDO:0004979"
    assert row["evidence_score"] == 1.0


def test_stats_and_decision():
    store = PacketStore(":memory:")
    store.insert_packet(_packet())
    assert store.get_stats() == {"UNREVIEWED": 1}
    store.record_decision(
        CurationDecision(
            id="d1",
            packet_id="sieve:pkt_1",
            curator="orcid:0000-0002-0000-0000",
            decision="ACCEPT",
            decided_at="2026-07-26T00:00:00",
        )
    )
