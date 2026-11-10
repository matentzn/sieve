"""The SIEVE schema is a conforming profile of the SEPIO core (snake_case derivation)."""

import importlib.util
import re
import sys

import pytest
from linkml.generators.jsonschemagen import JsonSchemaGenerator
from linkml_runtime.utils.schemaview import SchemaView

from sieve.datamodel.codegen import generate_pydantic
from sieve.traceability import CORE_SCHEMA, ROOT, SCHEMA

# sepio-framework/sepio-linkml src/sepio_linkml/schema/sepio_classes.yaml @ 8c2c233
CANONICAL_CORE = ROOT.parent / "sepio-linkml/src/sepio_linkml/schema/sepio_classes.yaml"
SNAKE = re.compile(r"^[a-z][a-z0-9_]*$")

# Slots whose core range is a plain string: a profile may narrow these to any
# datatype, enum or reference without widening the core.
STRING_LIKE = {"string", "uriorcurie", "uri"}


@pytest.fixture(scope="module")
def sv() -> SchemaView:
    return SchemaView(str(SCHEMA))


@pytest.fixture(scope="module")
def core() -> SchemaView:
    return SchemaView(str(CORE_SCHEMA))


@pytest.mark.skipif(not CANONICAL_CORE.exists(), reason="sepio-linkml not checked out next to sieve")
def test_core_is_derived_from_canonical():
    """sepio_core.yaml is exactly what scripts/snake_case_core.py makes of the canonical core."""
    spec = importlib.util.spec_from_file_location("snake_case_core", ROOT / "scripts" / "snake_case_core.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.render(CANONICAL_CORE) == CORE_SCHEMA.read_text(encoding="utf-8")


def test_core_keeps_canonical_slot_iris(core):
    """Renamed slots keep their canonical camelCase IRI."""
    slot = core.induced_slot("has_evidence_lines", "Statement")
    assert slot.slot_uri == "sepio-model:hasEvidenceLines"


def test_all_slots_are_snake_case(sv):
    """Slots are snake_case in core and profile; classes stay CamelCase."""
    for name, cls in sv.all_classes().items():
        assert name[0].isupper(), name
        for slot in sv.class_induced_slots(name):
            assert SNAKE.match(slot.name), f"{name}.{slot.name}"


def test_profile_does_not_redefine_core(sv, core):
    profile_classes = set(sv.all_classes(imports=False))
    assert not profile_classes & set(core.all_classes())
    assert not set(sv.all_enums(imports=False)) & set(core.all_enums())


def _core_ancestor(sv: SchemaView, core: SchemaView, name: str) -> str | None:
    for ancestor in sv.class_ancestors(name, mixins=False)[1:]:
        if ancestor in core.all_classes():
            return ancestor
    return None


def test_every_profile_class_specialises_a_core_class(sv, core):
    for name, cls in sv.all_classes(imports=False).items():
        if cls.mixin:
            continue
        assert _core_ancestor(sv, core, name), f"{name} has no SEPIO core ancestor"


def _narrows(sv: SchemaView, core_range: str, profile_range: str) -> bool:
    if core_range == profile_range or core_range in STRING_LIKE:
        return True
    if core_range in sv.all_types() or profile_range in sv.all_types():
        return False
    if profile_range in sv.class_descendants(core_range):
        return True
    # A profile mixin used as a range narrows the core class if every class using it
    # descends from that core class.
    mixin = sv.get_class(profile_range)
    if mixin is not None and mixin.mixin:
        users = [c for c, d in sv.all_classes().items() if profile_range in (d.mixins or [])]
        return all(core_range in sv.class_ancestors(u) for u in users)
    return False


def test_inherited_slots_only_narrow(sv, core):
    """Every slot a profile class inherits from the core keeps or narrows its range,
    keeps its cardinality and never relaxes `required`."""
    for name, cls in sv.all_classes(imports=False).items():
        if cls.mixin:
            continue
        ancestor = _core_ancestor(sv, core, name)
        assert ancestor
        core_slots = {s.name: s for s in core.class_induced_slots(ancestor)}
        for slot in sv.class_induced_slots(name):
            base = core_slots.get(slot.name)
            if base is None:
                continue
            where = f"{name}.{slot.name}"
            assert _narrows(sv, base.range or "string", slot.range or "string"), (where, base.range, slot.range)
            assert bool(base.multivalued) == bool(slot.multivalued), where
            assert not (base.required and not slot.required), where


def test_jsonschema_generates(sv):
    assert JsonSchemaGenerator(str(SCHEMA)).serialize()


def test_pydantic_generates_and_imports(tmp_path):
    target = tmp_path / "profile_models.py"
    target.write_text(generate_pydantic(SCHEMA))
    spec = importlib.util.spec_from_file_location("profile_models", target)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules["profile_models"] = module
    spec.loader.exec_module(module)
    assert issubclass(module.SynonymStatement, module.Statement)


def test_checked_in_models_are_current():
    committed = (ROOT / "src" / "sieve" / "datamodel" / "sieve_models.py").read_text()
    assert committed == generate_pydantic(SCHEMA), "run: just gen-pydantic"
