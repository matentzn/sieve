"""The example packet validates against sieve.yaml; a bad value fails."""

from pathlib import Path

import yaml
from linkml.validator import validate
from linkml_runtime import SchemaView

SIEVE = Path(__file__).parent.parent / "schema" / "sieve.yaml"
DATA = Path(__file__).parent / "data"


def _schema():
    # merge_imports resolves the sepio_classes import relative to the schema
    # dir; passing the schema path directly resolves imports against CWD.
    sv = SchemaView(str(SIEVE))
    sv.merge_imports()
    return sv.schema


def _load(rel):
    with open(DATA / rel, encoding="utf-8") as f:
        return yaml.safe_load(f)


def test_valid_example_packet_validates():
    report = validate(_load("valid/example_packet.yaml"), _schema(), "EvidencePacket")
    assert report.results == []


def test_bad_score_fails_validation():
    report = validate(_load("invalid/bad_score.yaml"), _schema(), "EvidencePacket")
    assert report.results  # at least one validation error (float expected, string given)


def test_stale_camelcase_key_is_rejected():
    """The snake_case flip is enforced: the pre-flip camelCase spelling of a slot
    is no longer a permitted field, so a packet using it fails validation."""
    packet = _load("valid/example_packet.yaml")
    packet["hasEvidenceLines"] = packet.pop("has_evidence_lines")
    report = validate(packet, _schema(), "EvidencePacket")
    assert report.results  # unknown slot 'hasEvidenceLines' must be rejected
