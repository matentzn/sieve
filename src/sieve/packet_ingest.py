"""Ingest YAML EvidencePackets into a PacketStore, with schema validation."""

from pathlib import Path
from typing import Any

from linkml.validator import validate
from linkml_runtime import SchemaView

from sieve.datamodel.loaders import load_packet
from sieve.store import PacketStore

SCHEMA_PATH = Path(__file__).parent.parent.parent / "schema" / "sieve.yaml"


def _merged_schema():
    # merge_imports resolves the sepio_classes import relative to the schema dir;
    # passing the schema path directly resolves imports against CWD.
    sv = SchemaView(str(SCHEMA_PATH))
    sv.merge_imports()
    return sv.schema


def validate_packet_dict(data: dict[str, Any]) -> list:
    """Return validation results ([] means valid) for a packet dict."""
    return validate(data, _merged_schema(), "EvidencePacket").results


def ingest_packet_file(path: Path, store: PacketStore) -> str:
    """Load, then store a single YAML EvidencePacket. Returns its id."""
    packet = load_packet(path)
    return store.insert_packet(packet)


def ingest_packet_directory(path: Path, store: PacketStore) -> dict[str, Any]:
    """Ingest every *.yaml/*.yml packet under a directory."""
    stats: dict[str, Any] = {"files": 0, "success": 0, "errors": 0, "error_details": []}
    for pattern in ("**/*.yaml", "**/*.yml"):
        for f in sorted(Path(path).glob(pattern)):
            stats["files"] += 1
            try:
                ingest_packet_file(f, store)
                stats["success"] += 1
            except Exception as e:  # noqa: BLE001 - report per-file, keep going
                stats["errors"] += 1
                stats["error_details"].append({"file": str(f), "error": str(e)})
    return stats
