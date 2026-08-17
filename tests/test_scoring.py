from sieve.datamodel import EvidencePacket, SieveEvidenceLine, SieveStatement
from sieve.scoring import net_evidence_ratio


def _packet(lines):
    return EvidencePacket(
        id="p",
        status="UNREVIEWED",
        statement=SieveStatement(id="s", type="SieveStatement", subject="MONDO:1", object="MONDO:2"),
        has_evidence_lines=lines,
    )


def test_all_supporting_is_plus_one():
    p = _packet(
        [
            SieveEvidenceLine(
                id="l1",
                type="SieveEvidenceLine",
                direction_of_evidence_provided="supports",
                score_of_evidence_provided=0.9,
            )
        ]
    )
    assert net_evidence_ratio(p) == 1.0


def test_mixed_directions():
    p = _packet(
        [
            SieveEvidenceLine(
                id="l1",
                type="SieveEvidenceLine",
                direction_of_evidence_provided="supports",
                score_of_evidence_provided=1.0,
            ),
            SieveEvidenceLine(
                id="l2",
                type="SieveEvidenceLine",
                direction_of_evidence_provided="disputes",
                score_of_evidence_provided=1.0,
            ),
        ]
    )
    assert net_evidence_ratio(p) == 0.0


def test_empty_is_zero():
    assert net_evidence_ratio(_packet([])) == 0.0


def test_qualitative_strength_fallback():
    p = _packet(
        [
            SieveEvidenceLine(
                id="l1",
                type="SieveEvidenceLine",
                direction_of_evidence_provided="supports",
                strength_of_evidence_provided="strong",
            )
        ]
    )
    assert net_evidence_ratio(p) == 1.0
