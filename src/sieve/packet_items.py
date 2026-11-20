"""The evidence items nested in an EvidencePacket.

Evidence is nested. A line carries its items in full (``has_evidence_items``), as
does a statement's direct evidence (``has_evidence``); a claim or passage carries the
record or document it is reported in (``reported_in``); and an origin event carries
the upstream item it copied (``source_item``). An item
used in several places is copied into each, under the same id, and the copies must
be identical. Evidence lines are items too: a higher-order line nests full copies of
the lines it reads.

This module walks those copies. It reads the packet as loaded from YAML / JSON and
needs no schema, so both ``sieve.profile_checks`` and ``sieve.inclusion_score`` use it.
"""

from typing import Any, Iterator

# Slots of an item that hold further nested items.
NESTED_ITEM_SLOTS = ("has_evidence_items", "reported_in")


def _as_list(value: Any) -> list:
    if value is None:
        return []
    return value if isinstance(value, list) else [value]


def _walk(item: dict) -> Iterator[dict]:
    yield item
    for slot in NESTED_ITEM_SLOTS:
        for child in _as_list(item.get(slot)):
            if isinstance(child, dict):
                yield from _walk(child)


def iter_items(packet: dict[str, Any]) -> Iterator[dict]:
    """Yield every evidence item in the packet, copies included, depth-first.

    The roots are the statement's evidence lines, its direct evidence (``has_evidence``),
    the items an origin event copied, and the records or documents the statement
    itself is reported in.

    >>> record = {"id": "OMIM:1", "type": "ExternalRecord"}
    >>> claim = {"id": "c1", "type": "SynonymStatement", "reported_in": [record]}
    >>> line = {"id": "l1", "type": "SieveEvidenceLine", "has_evidence_items": [claim]}
    >>> packet = {"statement": {"has_evidence_lines": [line], "origin": [{"source_item": dict(record)}]}}
    >>> [i["id"] for i in iter_items(packet)]
    ['l1', 'c1', 'OMIM:1', 'OMIM:1']
    """
    statement = packet["statement"]
    for line in statement.get("has_evidence_lines") or []:
        yield from _walk(line)
    for item in statement.get("has_evidence") or []:
        if isinstance(item, dict):
            yield from _walk(item)
    for origin in statement.get("origin") or []:
        source = origin.get("source_item")
        if isinstance(source, dict):
            yield from _walk(source)
    for document in _as_list(statement.get("reported_in")):
        if isinstance(document, dict):
            yield from _walk(document)


def item_copies(packet: dict[str, Any]) -> dict[str, list[dict]]:
    """Group every nested item by id: id -> all its copies, in walk order.

    >>> line = {"id": "l1", "type": "SieveEvidenceLine", "has_evidence_items": []}
    >>> synthesis = {"id": "l2", "type": "SieveEvidenceLine", "has_evidence_items": [dict(line)]}
    >>> {k: len(v) for k, v in item_copies({"statement": {"has_evidence_lines": [line, synthesis]}}).items()}
    {'l1': 2, 'l2': 1}
    """
    copies: dict[str, list[dict]] = {}
    for item in iter_items(packet):
        copies.setdefault(item["id"], []).append(item)
    return copies


def items_by_id(packet: dict[str, Any]) -> dict[str, dict]:
    """Index every nested item by id (the first copy found)."""
    return {item_id: found[0] for item_id, found in item_copies(packet).items()}


def find_item(packet: dict[str, Any], item_id: str) -> dict:
    """Return the first copy of the item with ``item_id``; KeyError if the packet has none."""
    return items_by_id(packet)[item_id]
