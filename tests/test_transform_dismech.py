"""The DisMech -> minimal linkml-map transform runs and its output validates.

Exercises transform/dismech_to_minimal.transform.yaml (the same command as the
`transform-dismech` recipe in project.justfile), then validates the output against
the minimal microschema.
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


def _map_data(spec, source_schema, source_type, in_path, out_path):
    cmd = [
        str(LINKML_MAP), "map-data",
        "-T", str(TRANSFORM / spec),
        "-s", str(source_schema),
        "--source-type", source_type,
        str(in_path),
        "-o", str(out_path),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    assert proc.returncode == 0, f"map-data failed:\n{proc.stderr}"
    with open(out_path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def test_dismech_to_minimal(tmp_path):
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
    # dismech's `supports` enum is split: SUPPORT and PARTIAL are both the SUPPORTS
    # *direction*; PARTIAL additionally sets strength WEAK (it is a strength, not a
    # direction).
    directions = {ln["direction_of_evidence_provided"] for ln in claim["has_evidence_lines"]}
    assert directions == {"SUPPORTS"}
    strengths = {ln.get("strength_of_evidence_provided") for ln in claim["has_evidence_lines"]}
    assert strengths == {None, "WEAK"}
    assert validate(claim, _schema("minimal.yaml"), "EvidencedClaim").results == []
