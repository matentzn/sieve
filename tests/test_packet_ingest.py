from pathlib import Path

import yaml

from sieve.packet_ingest import (
    ingest_packet_directory,
    ingest_packet_file,
    validate_packet_dict,
)
from sieve.store import PacketStore

VALID = Path(__file__).parent / "data" / "valid" / "example_packet.yaml"


def test_valid_packet_has_no_validation_errors():
    data = yaml.safe_load(VALID.read_text())
    assert validate_packet_dict(data) == []


def test_ingest_file_stores_packet():
    store = PacketStore(":memory:")
    pid = ingest_packet_file(VALID, store)
    assert store.get_packet(pid) is not None


def test_ingest_directory_counts(tmp_path):
    import shutil

    shutil.copy(VALID, tmp_path / "p.yaml")
    store = PacketStore(":memory:")
    stats = ingest_packet_directory(tmp_path, store)
    assert stats == {"files": 1, "success": 1, "errors": 0, "error_details": []}
