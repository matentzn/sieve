"""The DisMech -> minimal -> sieve linkml-map pipeline runs and both outputs validate.

Exercises the transforms in transform/ end to end (the same commands as the
`transform-*` recipes in project.justfile), then validates each output against its
target schema. Guards the minimal microschema and its compatibility with sieve.
"""

import subprocess
import sys
from pathlib import Path

import yaml
from linkml.validator import validate
from linkml_runtime import SchemaView

ROOT = Path(__file__).parent.parent
TRANSFORM = ROOT / "transform"
SCHEMA = ROOT / "schema"
LINKML_MAP = Path(sys.executable).parent / "linkml-map"


def _schema(name):
    sv = SchemaView(str(SCHEMA / name))
    sv.merge_imports()
    return sv.schema


def _map_data(spec, source_schema, source_type, in_path, out_path, unrestricted=False):
    cmd = [
        str(LINKML_MAP), "map-data",
        "-T", str(TRANSFORM / spec),
        "-s", str(source_schema),
        "--source-type", source_type,
        str(in_path),
        "-o", str(out_path),
    ]
    if unrestricted:
        cmd.insert(2, "--unrestricted-eval")
    proc = subprocess.run(cmd, capture_output=True, text=True)
    assert proc.returncode == 0, f"map-data failed:\n{proc.stderr}"
    with open(out_path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def test_dismech_to_minimal_then_sieve(tmp_path):
    # Stage 1: DisMech pathophysiology assertion -> minimal EvidencedClaim
    minimal_out = tmp_path / "fanconi_minimal.yaml"
    claim = _map_data(
        "dismech_to_minimal.transform.yaml",
        TRANSFORM / "dismech_source.yaml",
        "Pathophysiology",
        TRANSFORM / "dismech_fanconi_input.yaml",
        minimal_out,
    )
    # Two dismech evidence items -> two minimal evidence lines (one per item).
    assert len(claim["has_evidence_lines"]) == 2
    directions = {ln["direction_of_evidence_provided"] for ln in claim["has_evidence_lines"]}
    assert directions == {"SUPPORTS", "PARTIAL"}
    assert validate(claim, _schema("minimal.yaml"), "EvidencedClaim").results == []

    # Stage 2: minimal EvidencedClaim -> sieve EvidencePacket
    sieve_out = tmp_path / "fanconi_sieve.yaml"
    packet = _map_data(
        "minimal_to_sieve.transform.yaml",
        SCHEMA / "minimal.yaml",
        "EvidencedClaim",
        minimal_out,
        sieve_out,
        unrestricted=True,
    )
    # A minimal TextSpan lifts to a sieve SieveDocument (snippet -> quote).
    doc = packet["has_evidence_lines"][0]["has_evidence_items"][0]
    assert doc["type"] == "SieveDocument"
    assert doc["quote"]
    assert validate(packet, _schema("sieve.yaml"), "EvidencePacket").results == []
