"""The monarch_evidence corpus stays executable and stays in sync with the SPEC.

The nine example records in monarch_evidence/examples/ each render the same content
in the minimal microschema. Those `minimal:` blocks are real data, not illustration,
so they are validated against schema/minimal.yaml here — otherwise the next edit to
the kernel silently invalidates the corpus.

Five blocks legitimately fail, and only on the two enum values the corpus marks
PROPOSED and the SPEC tracks as Q7 (`EvidenceSource: REGULATORY`,
`DocumentType: REGULATORY_LABEL`). Any *other* failure is a real regression.
"""

import re
from pathlib import Path

import pytest
import yaml
from linkml.validator import validate
from linkml_runtime import SchemaView

ROOT = Path(__file__).parent.parent
CORPUS = ROOT / "monarch_evidence"
EXAMPLES = CORPUS / "examples"
SCHEMA = ROOT / "schema"

# Enum values the corpus deliberately uses ahead of the schema (SPEC Q7).
PROPOSED_VALUES = {"REGULATORY", "REGULATORY_LABEL"}

EXAMPLE_FILES = sorted(EXAMPLES.glob("*/*.yaml"))
REQUIRED_SECTIONS = {"id", "title", "source", "challenges", "summary", "as_is", "minimal", "gaps"}


@pytest.fixture(scope="module")
def minimal_schema():
    sv = SchemaView(str(SCHEMA / "minimal.yaml"))
    sv.merge_imports()
    return sv.schema


def _load(path):
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def _claim_blocks(record):
    """A `minimal:` block is either one EvidencedClaim or a list of them (D1)."""
    block = record["minimal"]
    blocks = block if isinstance(block, list) else [block]
    # `_host` is corpus annotation, not schema — see SPEC Q9.
    return [{k: v for k, v in b.items() if not k.startswith("_")} for b in blocks if isinstance(b, dict)]


def test_corpus_is_not_empty():
    assert len(EXAMPLE_FILES) == 9, f"expected 9 examples, found {len(EXAMPLE_FILES)}"


@pytest.mark.parametrize("path", EXAMPLE_FILES, ids=lambda p: p.stem)
def test_example_has_required_sections(path):
    record = _load(path)
    missing = REQUIRED_SECTIONS - set(record)
    assert not missing, f"{path.name} is missing sections: {sorted(missing)}"


@pytest.mark.parametrize("path", EXAMPLE_FILES, ids=lambda p: p.stem)
def test_minimal_blocks_validate(path, minimal_schema):
    """Every minimal block validates, or fails only on a documented PROPOSED value."""
    for i, claim in enumerate(_claim_blocks(_load(path))):
        results = validate(claim, minimal_schema, "EvidencedClaim").results
        for result in results:
            offending = re.findall(r"'([A-Z_]+)' is not one of", result.message)
            assert offending, f"{path.name}[{i}]: unexpected failure: {result.message}"
            assert set(offending) <= PROPOSED_VALUES, (
                f"{path.name}[{i}]: fails on a value that is not a documented "
                f"PROPOSED one: {sorted(set(offending) - PROPOSED_VALUES)}"
            )


@pytest.mark.parametrize("path", EXAMPLE_FILES, ids=lambda p: p.stem)
def test_declared_challenges_exist_in_spec(path):
    """No example may cite a requirement the SPEC does not define."""
    spec = (CORPUS / "SPEC.md").read_text(encoding="utf-8")
    defined = set(re.findall(r"^\| \*\*(R\d+)\*\*", spec, re.M))
    assert defined, "no requirement rows parsed out of SPEC.md — table format changed?"
    cited = {c for c in _load(path)["challenges"] if c.startswith("R")}
    assert cited <= defined, f"{path.name} cites undefined requirements: {sorted(cited - defined)}"
