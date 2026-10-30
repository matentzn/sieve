"""Every example in the repo is expressed in the SIEVE profile and validates.

- ``inbox/examples/*.yaml``: ingestable EvidencePackets.
- ``tests/data/valid`` / ``tests/data/invalid``: fixtures for the legacy loaders, now
  in the profile shape (the invalid one must still fail).
- ``monarch_evidence/examples/*/*.yaml``: the ``sepio_monarch`` block is either a
  packet (or list of packets), or, when the claim is outside the Mondo-driven profile
  (DisMech mechanisms, MeDIC indications), ``{misfit, fragments}``: the parts that
  do fit, each validated against its own class. A record with fragments must explain
  the misfit in ``gaps.profile_misfit``.
"""

from pathlib import Path

import pytest

from tests.profile_support import load_yaml, packet_problems, schema_errors

ROOT = Path(__file__).parent.parent
INBOX = sorted((ROOT / "inbox" / "examples").glob("*.yaml"))
CORPUS = sorted((ROOT / "monarch_evidence" / "examples").glob("*/*.yaml"))


def _strip_private(value):
    """Drop corpus annotation keys (leading underscore), recursively."""
    if isinstance(value, dict):
        return {k: _strip_private(v) for k, v in value.items() if not str(k).startswith("_")}
    if isinstance(value, list):
        return [_strip_private(v) for v in value]
    return value


@pytest.mark.parametrize("path", INBOX, ids=lambda p: p.stem)
def test_inbox_packets(path):
    assert packet_problems(load_yaml(path)) == []


def test_valid_fixture():
    assert packet_problems(load_yaml(ROOT / "tests/data/valid/example_packet.yaml")) == []


def test_invalid_fixture_fails_on_score():
    problems = packet_problems(load_yaml(ROOT / "tests/data/invalid/bad_score.yaml"))
    assert problems
    assert any("score" in p.lower() or "maximum" in p for p in problems)


@pytest.mark.parametrize("path", CORPUS, ids=lambda p: p.stem)
def test_corpus_sepio_block(path):
    record = load_yaml(path)
    block = _strip_private(record["sepio_monarch"])
    if isinstance(block, list) or "statement" in block:
        for packet in block if isinstance(block, list) else [block]:
            assert packet_problems(packet) == [], packet.get("id")
        return
    assert set(block) == {"misfit", "fragments"}, f"{path.name}: sepio_monarch is neither a packet nor misfit+fragments"
    assert str(block["misfit"]).strip()
    assert "profile_misfit" in record["gaps"], f"{path.name}: misfit not recorded in gaps"
    assert block["fragments"], f"{path.name}: no fragments"
    for fragment in block["fragments"]:
        cls = fragment["class"]
        assert schema_errors(fragment["data"], cls) == [], f"{path.name}: fragment {fragment['data'].get('id')} as {cls}"
