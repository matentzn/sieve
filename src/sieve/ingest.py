"""Ingest YAML files into the curation database."""

from datetime import datetime
from pathlib import Path
from uuid import uuid4

import yaml

from sieve.db import CurationDatabase
from sieve.models import (
    Assertion,
    AssertionProvenance,
    CurationActivity,
    CurationRecord,
    CurationStatus,
    EvidenceDirection,
    EvidenceItem,
    EvidenceSynthesis,
    EvidenceType,
    SourceType,
)


def generate_id() -> str:
    """Generate a unique record ID."""
    return f"cura:{uuid4().hex[:12]}"


def load_yaml_file(path: Path) -> dict:
    """Load a YAML file."""
    with open(path, "r") as f:
        return yaml.safe_load(f)


def parse_curation_record(data: dict) -> CurationRecord:
    """Parse a dictionary into a CurationRecord."""

    # Parse assertion
    assertion_data = data.get("assertion", {})
    assertion = Assertion(
        subject_id=assertion_data.get("subject_id"),
        subject_label=assertion_data.get("subject_label"),
        predicate=assertion_data.get("predicate"),
        predicate_label=assertion_data.get("predicate_label"),
        object_id=assertion_data.get("object_id"),
        object_label=assertion_data.get("object_label"),
        display_text=assertion_data.get("display_text"),
    )

    # Parse provenance
    provenance = None
    if "provenance" in data:
        prov_data = data["provenance"]

        # Parse nested activity if present
        generated_by = None
        if "generated_by" in prov_data:
            act_data = prov_data["generated_by"]
            generated_by = CurationActivity(
                id=act_data.get("id"),
                description=act_data.get("description"),
                associated_with=act_data.get("associated_with"),
                associated_with_labels=act_data.get("associated_with_labels"),
                started_at=act_data.get("started_at"),
                ended_at=act_data.get("ended_at"),
                created_with=act_data.get("created_with"),
                pull_request=act_data.get("pull_request"),
            )

        provenance = AssertionProvenance(
            attributed_to=prov_data.get("attributed_to"),
            generated_at=prov_data.get("generated_at"),
            source_version=prov_data.get("source_version"),
            source_uri=prov_data.get("source_uri"),
            generated_by=generated_by,
        )

    # Parse evidence items
    evidence = []
    for ev_data in data.get("evidence", []):
        evidence_type_str = ev_data.get("evidence_type", "OTHER")
        try:
            evidence_type = EvidenceType(evidence_type_str)
        except ValueError:
            evidence_type = EvidenceType.OTHER

        # Parse source_type if present
        source_type = None
        source_type_str = ev_data.get("source_type")
        if source_type_str:
            try:
                source_type = SourceType(source_type_str)
            except ValueError:
                source_type = SourceType.OTHER

        # Parse direction if present (defaults to SUPPORTS)
        direction = EvidenceDirection.SUPPORTS
        direction_str = ev_data.get("direction")
        if direction_str:
            try:
                direction = EvidenceDirection(direction_str)
            except ValueError:
                direction = EvidenceDirection.SUPPORTS

        # Parse evidence_strength if present (defaults to 1.0)
        evidence_strength = ev_data.get("evidence_strength", 1.0)
        evidence_strength = max(0.0, min(1.0, float(evidence_strength)))

        evidence.append(
            EvidenceItem(
                id=ev_data.get("id", generate_id()),
                evidence_type=evidence_type,
                direction=direction,
                evidence_strength=evidence_strength,
                eco_code=ev_data.get("eco_code"),
                eco_label=ev_data.get("eco_label"),
                description=ev_data.get("description"),
                # Concordance fields
                source=ev_data.get("source"),
                source_name=ev_data.get("source_name"),
                source_type=source_type,
                predicate_id=ev_data.get("predicate_id"),
                predicate_label=ev_data.get("predicate_label"),
                source_subject_id=ev_data.get("source_subject_id"),
                source_subject_label=ev_data.get("source_subject_label"),
                source_object_id=ev_data.get("source_object_id"),
                source_object_label=ev_data.get("source_object_label"),
                mapping_set=ev_data.get("mapping_set"),
                # Literature fields
                publication_id=ev_data.get("publication_id"),
                publication_title=ev_data.get("publication_title"),
                quoted_text=ev_data.get("quoted_text"),
                quote_location=ev_data.get("quote_location"),
                explanation=ev_data.get("explanation"),
                # Expert review fields
                reviewer_orcid=ev_data.get("reviewer_orcid"),
                reviewer_name=ev_data.get("reviewer_name"),
                reviewer_affiliation=ev_data.get("reviewer_affiliation"),
                reviewed_at=ev_data.get("reviewed_at"),
                issue=ev_data.get("issue"),
            )
        )

    status_str = data.get("status", "UNREVIEWED")
    try:
        status = CurationStatus(status_str)
    except ValueError:
        status = CurationStatus.UNREVIEWED

    # Parse evidence synthesis if present
    evidence_synthesis = None
    if "evidence_synthesis" in data:
        synth_data = data["evidence_synthesis"]
        evidence_synthesis = EvidenceSynthesis(
            summary=synth_data.get("summary"),
            confidence=synth_data.get("confidence"),
        )

    return CurationRecord(
        id=data.get("id", generate_id()),
        last_updated=data.get("last_updated"),
        assertion=assertion,
        provenance=provenance,
        evidence=evidence,
        evidence_synthesis=evidence_synthesis,
        status=status,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )


def ingest_file(path: Path, db: CurationDatabase) -> tuple[int, int]:
    """
    Ingest a YAML file into the database.
    Returns (success_count, skip_count).
    """
    data = load_yaml_file(path)

    # Handle single record or list of records
    records = data if isinstance(data, list) else [data]

    success = 0
    skipped = 0

    for record_data in records:
        record = parse_curation_record(record_data)

        # Skip if already exists
        if db.record_exists(record.id):
            skipped += 1
            continue

        db.insert_record(record)
        success += 1

    return success, skipped


def ingest_directory(inbox_path: Path, db: CurationDatabase) -> dict:
    """
    Ingest all YAML files from a directory.
    Returns summary statistics.
    """
    inbox = Path(inbox_path)
    if not inbox.exists():
        inbox.mkdir(parents=True)
        return {"files": 0, "success": 0, "skipped": 0, "errors": 0}

    stats = {"files": 0, "success": 0, "skipped": 0, "errors": 0, "error_details": []}

    for yaml_file in inbox.glob("**/*.yaml"):
        stats["files"] += 1
        try:
            success, skipped = ingest_file(yaml_file, db)
            stats["success"] += success
            stats["skipped"] += skipped
        except Exception as e:
            stats["errors"] += 1
            stats["error_details"].append({"file": str(yaml_file), "error": str(e)})

    for yml_file in inbox.glob("**/*.yml"):
        stats["files"] += 1
        try:
            success, skipped = ingest_file(yml_file, db)
            stats["success"] += success
            stats["skipped"] += skipped
        except Exception as e:
            stats["errors"] += 1
            stats["error_details"].append({"file": str(yml_file), "error": str(e)})

    return stats
