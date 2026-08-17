"""The canonical SIEVE model compiles and exposes EvidencePacket."""

from pathlib import Path

from linkml.generators.jsonschemagen import JsonSchemaGenerator
from linkml_runtime import SchemaView

SIEVE = Path(__file__).parent.parent / "schema" / "sieve.yaml"


def test_sieve_schema_generates_json_schema():
    JsonSchemaGenerator(str(SIEVE)).serialize()


def test_evidence_packet_is_tree_root():
    sv = SchemaView(str(SIEVE))
    packet = sv.get_class("EvidencePacket")
    assert packet is not None
    assert packet.tree_root is True
