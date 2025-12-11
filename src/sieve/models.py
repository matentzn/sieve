"""Pydantic models for the curation application.

These models can be generated from the LinkML schema using:
    gen-pydantic schema/curation_model.yaml > src/curation_app/models.py

For now, we define them manually for simplicity.
"""

from datetime import date, datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class CurationStatus(str, Enum):
    """Status of a curation record."""

    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    DEFERRED = "DEFERRED"


class DecisionType(str, Enum):
    """Type of curation decision."""

    ACCEPT = "ACCEPT"
    REJECT = "REJECT"
    DEFER = "DEFER"


class EvidenceType(str, Enum):
    """Type of evidence supporting an assertion."""

    CONCORDANCE = "CONCORDANCE"
    LITERATURE = "LITERATURE"
    EXPERT_REVIEW = "EXPERT_REVIEW"
    COMPUTATIONAL = "COMPUTATIONAL"
    OTHER = "OTHER"


class ArtifactType(str, Enum):
    """Type of source artifact."""

    NANOPUB = "NANOPUB"
    YAML_FILE = "YAML_FILE"
    JSON_FILE = "JSON_FILE"


class Assertion(BaseModel):
    """The statement being curated (typically an ontology axiom)."""

    subject_id: str
    subject_label: Optional[str] = None
    predicate: str
    predicate_label: Optional[str] = None
    object_id: str
    object_label: Optional[str] = None


class AssertionProvenance(BaseModel):
    """Origin and attribution of the assertion."""

    attributed_to: Optional[str] = None
    attributed_to_label: Optional[str] = None
    generated_at: Optional[date] = None
    source_version: Optional[str] = None
    source_uri: Optional[str] = None


class EvidenceItem(BaseModel):
    """A piece of evidence supporting the assertion."""

    id: Optional[str] = None
    evidence_type: EvidenceType
    eco_code: Optional[str] = None
    eco_label: Optional[str] = None
    description: Optional[str] = None

    # Concordance-specific fields
    source_ontology: Optional[str] = None
    source_subject_id: Optional[str] = None
    source_subject_label: Optional[str] = None
    source_object_id: Optional[str] = None
    source_object_label: Optional[str] = None
    mapping_set_uri: Optional[str] = None

    # Literature-specific fields
    publication_id: Optional[str] = None
    publication_title: Optional[str] = None
    quoted_text: Optional[str] = None
    quote_location: Optional[str] = None

    # Expert review-specific fields
    reviewer_orcid: Optional[str] = None
    reviewer_name: Optional[str] = None
    reviewer_affiliation: Optional[str] = None
    reviewed_at: Optional[date] = None


class CurationRecord(BaseModel):
    """A candidate assertion with supporting evidence for curation review."""

    id: str
    assertion: Assertion
    provenance: Optional[AssertionProvenance] = None
    evidence_items: Optional[list[EvidenceItem]] = Field(default_factory=list)
    source_artifact_uri: Optional[str] = None
    source_artifact_type: Optional[str] = None
    status: CurationStatus = CurationStatus.PENDING
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class CurationDecision(BaseModel):
    """A curator's decision on a CurationRecord."""

    id: str
    record_id: str
    curator_orcid: str
    curator_name: Optional[str] = None
    decision: DecisionType
    rationale: Optional[str] = None
    decided_at: datetime
