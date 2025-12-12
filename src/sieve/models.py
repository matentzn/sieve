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

    UNREVIEWED = "UNREVIEWED"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    CONTROVERSIAL = "CONTROVERSIAL"


class DecisionType(str, Enum):
    """Type of curation decision."""

    ACCEPT = "ACCEPT"
    REJECT = "REJECT"
    CONTROVERSIAL = "CONTROVERSIAL"


class EvidenceType(str, Enum):
    """Type of evidence supporting an assertion."""

    CONCORDANCE = "CONCORDANCE"
    LITERATURE = "LITERATURE"
    EXPERT_REVIEW = "EXPERT_REVIEW"
    COMPUTATIONAL = "COMPUTATIONAL"
    OTHER = "OTHER"


class SourceType(str, Enum):
    """Type of concordance source."""

    ONTOLOGY = "ONTOLOGY"
    TERMINOLOGY = "TERMINOLOGY"
    DATABASE = "DATABASE"
    OTHER = "OTHER"


class EvidenceDirection(str, Enum):
    """Whether the evidence supports or contradicts the assertion."""

    SUPPORTS = "SUPPORTS"
    CONTRADICTS = "CONTRADICTS"
    UNCERTAIN = "UNCERTAIN"


class Assertion(BaseModel):
    """The statement being curated (typically an ontology axiom)."""

    subject_id: str
    subject_label: Optional[str] = None
    predicate: str
    predicate_label: Optional[str] = None
    object_id: str
    object_label: Optional[str] = None
    display_text: Optional[str] = None


class CurationActivity(BaseModel):
    """A curation activity that generated or modified an assertion."""

    id: Optional[str] = None
    description: Optional[str] = None
    associated_with: Optional[list[str]] = None
    associated_with_labels: Optional[list[str]] = None
    started_at: Optional[date] = None
    ended_at: Optional[date] = None
    created_with: Optional[str] = None
    pull_request: Optional[str] = None


class AssertionProvenance(BaseModel):
    """Origin and attribution of the assertion."""

    attributed_to: Optional[list[str]] = None
    generated_at: Optional[date] = None
    source_version: Optional[str] = None
    source_uri: Optional[str] = None
    generated_by: Optional[CurationActivity] = None


class Evidence(BaseModel):
    """A piece of evidence supporting or contradicting the assertion.

    This is a flat representation that can hold any evidence subtype fields.
    The evidence_type field indicates which subclass this corresponds to.
    """

    id: Optional[str] = None
    evidence_type: EvidenceType
    direction: EvidenceDirection = EvidenceDirection.SUPPORTS
    evidence_strength: float = Field(default=1.0, ge=0.0, le=1.0)
    eco_code: Optional[str] = None
    eco_label: Optional[str] = None
    description: Optional[str] = None

    # Concordance-specific fields
    source: Optional[str] = None
    source_name: Optional[str] = None
    source_type: Optional[SourceType] = None
    predicate_id: Optional[str] = None
    predicate_label: Optional[str] = None
    source_subject_id: Optional[str] = None
    source_subject_label: Optional[str] = None
    source_object_id: Optional[str] = None
    source_object_label: Optional[str] = None
    mapping_set: Optional[str] = None

    # Literature-specific fields
    publication_id: Optional[str] = None
    publication_title: Optional[str] = None
    quoted_text: Optional[str] = None
    quote_location: Optional[str] = None
    explanation: Optional[str] = None

    # Expert review-specific fields
    reviewer_orcid: Optional[str] = None
    reviewer_name: Optional[str] = None
    reviewer_affiliation: Optional[str] = None
    reviewed_at: Optional[date] = None
    issue: Optional[str] = None

    # Computational-specific fields
    method: Optional[str] = None
    method_uri: Optional[str] = None
    confidence_score: Optional[float] = None
    parameters: Optional[str] = None


# Alias for backwards compatibility
EvidenceItem = Evidence


class CurationRecord(BaseModel):
    """A candidate assertion with supporting evidence for curation review."""

    id: str
    last_updated: Optional[date] = None
    assertion: Assertion
    provenance: Optional[AssertionProvenance] = None
    evidence: Optional[list[Evidence]] = Field(default_factory=list)
    status: CurationStatus = CurationStatus.UNREVIEWED
    evidence_steward: Optional[str] = None
    confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class CurationDecision(BaseModel):
    """A curator's decision on a CurationRecord."""

    id: str
    record_id: str
    curator_orcid: str
    curator_name: Optional[str] = None
    decision: DecisionType
    certainty: float = Field(default=1.0, ge=0.0, le=1.0)
    rationale: Optional[str] = None
    decided_at: datetime
