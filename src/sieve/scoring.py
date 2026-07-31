"""Net Evidence Ratio scoring over SEPIO EvidenceLines."""

from sieve.datamodel import EvidencePacket

_STRENGTH = {"strong": 1.0, "moderate": 0.6, "weak": 0.3}


def line_score(line) -> float:
    """Numeric weight of an evidence line: explicit score, else strength, else 1.0."""
    if line.score_of_evidence_provided is not None:
        return float(line.score_of_evidence_provided)
    return _STRENGTH.get(line.strength_of_evidence_provided or "", 1.0)


def net_evidence_ratio(packet: EvidencePacket) -> float:
    """NER = (S+ - S-) / (S+ + S- + S0) over lines; range [-1, +1]."""
    s_plus = s_minus = s_zero = 0.0
    for line in packet.has_evidence_lines or []:
        w = line_score(line)
        direction = (line.direction_of_evidence_provided or "neutral").lower()
        if direction == "supports":
            s_plus += w
        elif direction == "disputes":
            s_minus += w
        else:
            s_zero += w
    total = s_plus + s_minus + s_zero
    return (s_plus - s_minus) / total if total else 0.0
