from pathlib import Path

import yaml

from sieve.datamodel import ConcordanceItem
from sieve.datamodel.loaders import load_packet, packet_from_dict
from sieve.packet_export import export_packets_to_yaml, packet_to_yaml

EX = Path(__file__).parent.parent / "inbox" / "examples" / "asthma_subclass.sepio.yaml"


def test_yaml_roundtrip_preserves_subject_and_items():
    packet = load_packet(EX)
    reloaded = packet_from_dict(yaml.safe_load(packet_to_yaml(packet)))
    assert reloaded.statement.subject == "MONDO:0004979"
    assert isinstance(reloaded.hasEvidenceLines[0].hasEvidenceItems[0], ConcordanceItem)


def test_export_multi_document(tmp_path):
    packet = load_packet(EX)
    out = tmp_path / "packets.yaml"
    export_packets_to_yaml([packet, packet], out)
    docs = list(yaml.safe_load_all(out.read_text()))
    assert len(docs) == 2
    assert docs[0]["id"] == "http://purl.org/np/RA9876543210"
