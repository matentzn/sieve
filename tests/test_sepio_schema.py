"""The SEPIO base schema must be present and compile to a JSON Schema."""

from pathlib import Path

from linkml.generators.jsonschemagen import JsonSchemaGenerator

SEPIO = Path(__file__).parent.parent / "schema" / "sepio_classes.yaml"


def test_sepio_schema_exists():
    assert SEPIO.exists()


def test_sepio_schema_generates_json_schema():
    # Must not raise — proves the schema is internally consistent.
    JsonSchemaGenerator(str(SEPIO)).serialize()
