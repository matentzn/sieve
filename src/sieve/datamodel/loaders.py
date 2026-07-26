"""Load SIEVE EvidencePackets with correct evidence-item polymorphism.

Evidence items are a union of InformationEntity subclasses; Pydantic's default
deserialization through the base class drops subclass fields. We dispatch each
item to its concrete class by the item's ``type`` field before validating.
"""

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel

from sieve.datamodel.sieve_models import (
    AgentContribution,
    ComputationalResult,
    ConcordanceItem,
    EvidencePacket,
    SieveDataItem,
    SieveDocument,
    SieveStudyResult,
)

EVIDENCE_ITEM_TYPES: dict[str, type[BaseModel]] = {
    "ConcordanceItem": ConcordanceItem,
    "AgentContribution": AgentContribution,
    "ComputationalResult": ComputationalResult,
    "SieveDocument": SieveDocument,
    "SieveDataItem": SieveDataItem,
    "SieveStudyResult": SieveStudyResult,
    # base-type aliases
    "Document": SieveDocument,
    "DataItem": SieveDataItem,
    "StudyResult": SieveStudyResult,
}


def _convert_evidence_items(data: dict[str, Any]) -> dict[str, Any]:
    for line in data.get("hasEvidenceLines") or []:
        items = line.get("hasEvidenceItems")
        if not items:
            continue
        converted: list[Any] = []
        for item in items:
            if isinstance(item, dict):
                cls = EVIDENCE_ITEM_TYPES.get(item.get("type", ""))
                converted.append(cls.model_validate(item) if cls else item)
            else:
                converted.append(item)
        line["hasEvidenceItems"] = converted
    return data


def packet_from_dict(data: dict[str, Any]) -> EvidencePacket:
    """Build an EvidencePacket from a raw dict, dispatching evidence items."""
    return EvidencePacket.model_validate(_convert_evidence_items(dict(data)))


def load_packet(path: Path) -> EvidencePacket:
    """Load an EvidencePacket from a YAML file."""
    with open(path, encoding="utf-8") as f:
        return packet_from_dict(yaml.safe_load(f))
