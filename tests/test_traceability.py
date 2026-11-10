"""Requirement traceability: spreadsheet rows <-> traceability.yaml <-> schema annotations."""

import re

import pytest
from linkml_runtime.utils.schemaview import SchemaView

from sieve.traceability import (
    ANNOTATED_DISPOSITIONS,
    CORE_SCHEMA,
    DISPOSITIONS,
    ROOT,
    SCHEMA,
    collect_annotations,
    load_requirements,
    load_traceability,
    render_markdown,
)

WORKBOOK = (
    ROOT.parent.parent
    / "notes/evidence/background/mondo-requirements/Mondo_Requirements_Collection_Forms.xlsx"
)


@pytest.fixture(scope="module")
def sv() -> SchemaView:
    return SchemaView(str(SCHEMA))


@pytest.fixture(scope="module")
def requirements() -> dict:
    return load_requirements()


@pytest.fixture(scope="module")
def trace() -> dict:
    return load_traceability()


def test_every_requirement_has_a_trace_entry(requirements, trace):
    assert set(requirements) == set(trace["requirements"])


def test_trace_entries_are_well_formed(trace):
    for rid, entry in trace["requirements"].items():
        assert entry["module"] in trace["modules"], rid
        assert entry["disposition"] in DISPOSITIONS, rid
        assert str(entry.get("rationale", "")).strip(), f"{rid} has no rationale"
        for decision in entry.get("decisions", []):
            assert re.fullmatch(r"D-\d{3}", decision), (rid, decision)


def test_not_desired_matches_spreadsheet(requirements, trace):
    """F2 = N rows are not_desired or negative_constraint; Y/M rows are neither."""
    negative = ("not_desired", "negative_constraint")
    for rid, entry in trace["requirements"].items():
        desired = requirements[rid]["desired"]
        assert (entry["disposition"] in negative) == (desired == "N"), (rid, desired, entry["disposition"])


def test_modelled_iff_annotated(sv, trace):
    index = collect_annotations(sv)
    for rid, entry in trace["requirements"].items():
        if entry["disposition"] in ANNOTATED_DISPOSITIONS:
            assert index.get(rid), f"{rid} is {entry['disposition']} but no schema element carries it"
        else:
            assert not index.get(rid), f"{rid} is {entry['disposition']} but annotated on {index[rid]}"


def test_annotations_reference_known_requirements(sv, requirements):
    unknown = set(collect_annotations(sv)) - set(requirements)
    assert not unknown


def test_decision_annotations_are_well_formed(sv):
    for decision in collect_annotations(sv, key="decisions"):
        assert re.fullmatch(r"D-\d{3}", decision), decision


def test_module_core_classes_exist_in_sepio_core(trace):
    core = SchemaView(str(CORE_SCHEMA))
    for key, module in trace["modules"].items():
        for cls in module["core_classes"]:
            assert cls in core.all_classes(), (key, cls)


def test_rendered_doc_is_current(sv):
    doc = ROOT / "docs" / "requirements-traceability.md"
    assert doc.read_text() == render_markdown(sv), "run: uv run python scripts/render_traceability.py"


@pytest.mark.skipif(not WORKBOOK.exists(), reason="requirements workbook not checked out next to sieve")
def test_tsv_matches_workbook(requirements):
    """The checked-in TSV is a faithful extract of the workbook."""
    import importlib.util

    spec = importlib.util.spec_from_file_location("extract", ROOT / "scripts" / "extract_requirements.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    extracted = {row["id"]: row for row in module.extract(WORKBOOK)}
    assert extracted == requirements
