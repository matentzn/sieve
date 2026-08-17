"""CLI smoke test over the new EvidencePacket stack."""

import shutil
from pathlib import Path

from typer.testing import CliRunner

from sieve.cli import app

runner = CliRunner()
EX = Path(__file__).parent.parent / "inbox" / "examples" / "asthma_subclass.sepio.yaml"


def test_validate_ok():
    result = runner.invoke(app, ["validate", "-i", str(EX)])
    assert result.exit_code == 0, result.output
    assert "0 total error(s)" in result.output


def test_ingest_and_export(tmp_path):
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    shutil.copy(EX, inbox / "p.yaml")
    db = tmp_path / "sieve.duckdb"

    r_ingest = runner.invoke(app, ["ingest", "-I", str(inbox), "--db", str(db)])
    assert r_ingest.exit_code == 0, r_ingest.output
    assert "Ingested 1 of 1" in r_ingest.output

    out_ttl = tmp_path / "out.ttl"
    r_rdf = runner.invoke(app, ["export", "-i", str(EX), "-O", "rdf", "-o", str(out_ttl)])
    assert r_rdf.exit_code == 0, r_rdf.output
    assert out_ttl.exists()
    assert "owl:Axiom" in out_ttl.read_text()

    out_yaml = tmp_path / "out.yaml"
    r_yaml = runner.invoke(app, ["export", "-i", str(EX), "-O", "yaml", "-o", str(out_yaml)])
    assert r_yaml.exit_code == 0, r_yaml.output
    assert out_yaml.exists()
