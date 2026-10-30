"""Shared helpers for validating data against the SIEVE profile in tests."""

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from linkml.validator import Validator
from linkml.validator.plugins import JsonschemaValidationPlugin
from linkml_runtime.utils.schemaview import SchemaView

from sieve.profile_checks import check_packet
from sieve.traceability import SCHEMA


class StringDateLoader(yaml.SafeLoader):
    """SafeLoader that keeps ISO dates as strings, as the JSON-Schema validator expects."""


StringDateLoader.yaml_implicit_resolvers = {
    key: [(tag, regexp) for tag, regexp in resolvers if tag != "tag:yaml.org,2002:timestamp"]
    for key, resolvers in yaml.SafeLoader.yaml_implicit_resolvers.items()
}


def load_yaml(path: Path) -> Any:
    """Load YAML with dates kept as strings."""
    with path.open(encoding="utf-8") as fh:
        return yaml.load(fh, Loader=StringDateLoader)  # noqa: S506 - SafeLoader subclass


@lru_cache(maxsize=1)
def profile_validator() -> Validator:
    """A closed JSON-Schema validator for the merged profile."""
    sv = SchemaView(str(SCHEMA))
    sv.merge_imports()
    return Validator(sv.schema, validation_plugins=[JsonschemaValidationPlugin(closed=True)])


def schema_errors(instance: dict, target: str = "EvidencePacket") -> list[str]:
    """Return the linkml-validate messages for ``instance`` as ``target``."""
    return [r.message for r in profile_validator().validate(instance, target).results]


def packet_problems(packet: dict) -> list[str]:
    """Schema errors plus profile-check ERRORs for one EvidencePacket.

    The statement is also validated against its concrete claim type, because inside a
    packet it is polymorphic and the JSON-Schema anyOf hides the specific reason.
    """
    problems = schema_errors(packet)
    statement = packet.get("statement") or {}
    if problems and statement.get("type"):
        problems += [f"statement: {m}" for m in schema_errors(statement, statement["type"])]
    if not problems:
        problems += [f"{i.code}: {i.message}" for i in check_packet(packet) if i.severity == "ERROR"]
    return problems
