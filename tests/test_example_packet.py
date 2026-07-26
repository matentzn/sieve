from pathlib import Path

import yaml

from sieve.datamodel.loaders import load_packet
from sieve.packet_ingest import validate_packet_dict

EX = Path(__file__).parent.parent / "inbox" / "examples" / "asthma_subclass.sepio.yaml"


def test_example_validates():
    assert validate_packet_dict(yaml.safe_load(EX.read_text())) == []


def test_example_has_all_item_types():
    packet = load_packet(EX)
    types = {
        type(i).__name__
        for line in packet.hasEvidenceLines
        for i in line.hasEvidenceItems
    }
    assert {
        "ConcordanceItem",
        "SieveDocument",
        "AgentContribution",
        "ComputationalResult",
    } <= types
