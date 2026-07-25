"""Export curation records as YAML packages."""

import io
import tarfile
from datetime import datetime
from pathlib import Path
from typing import Generator

import yaml

from sieve.db import CurationDatabase


def record_to_export_dict(record: dict, decision: dict | None = None) -> dict:
    """Convert a database record to an exportable dictionary.

    This creates a complete evidence packet with slots in order:
    id, status, last_updated, evidence_steward, confidence, assertion, provenance, evidence

    Args:
        record: Database record dict
        decision: Optional decision dict (most recent decision for this record)

    Returns:
        Dictionary suitable for YAML export with keys in canonical order
    """
    # Build assertion
    assertion = {
        "subject_id": record.get("assertion_subject_id"),
        "predicate": record.get("assertion_predicate"),
        "object_id": record.get("assertion_object_id"),
    }
    if record.get("assertion_subject_label"):
        assertion["subject_label"] = record["assertion_subject_label"]
    if record.get("assertion_predicate_label"):
        assertion["predicate_label"] = record["assertion_predicate_label"]
    if record.get("assertion_object_label"):
        assertion["object_label"] = record["assertion_object_label"]
    if record.get("assertion_display_text"):
        assertion["display_text"] = record["assertion_display_text"]

    # Build evidence list
    evidence_list = list(record.get("evidence") or [])

    # Add the review decision as an EXPERT_REVIEW evidence item
    if decision:
        review_evidence = {
            "id": decision.get("id"),
            "evidence_type": "EXPERT_REVIEW",
            "direction": "SUPPORTS" if decision.get("decision") == "ACCEPT" else "CONTRADICTS",
            "evidence_strength": decision.get("certainty", 1.0),
            "description": f"Curator decision: {decision.get('decision')}",
        }

        if decision.get("curator_orcid"):
            review_evidence["reviewer_orcid"] = decision["curator_orcid"]
        if decision.get("curator_name"):
            review_evidence["reviewer_name"] = decision["curator_name"]
        if decision.get("decided_at"):
            decided_at = decision["decided_at"]
            if hasattr(decided_at, "date"):
                review_evidence["reviewed_at"] = decided_at.date().isoformat()
            elif hasattr(decided_at, "isoformat"):
                review_evidence["reviewed_at"] = decided_at.isoformat()
            else:
                review_evidence["reviewed_at"] = str(decided_at)[:10]
        if decision.get("rationale"):
            review_evidence["description"] = (
                f"Curator decision: {decision.get('decision')}. "
                f"Rationale: {decision.get('rationale')}"
            )

        evidence_list.append(review_evidence)

    # Build export dict in canonical order:
    # id, status, last_updated, evidence_steward, confidence, assertion, provenance, evidence
    export = {"id": record.get("id")}
    export["status"] = record.get("status")

    # last_updated
    if record.get("last_updated"):
        last_updated = record["last_updated"]
        if hasattr(last_updated, "isoformat"):
            export["last_updated"] = last_updated.isoformat()
        else:
            export["last_updated"] = str(last_updated)

    # evidence_steward
    if record.get("evidence_steward"):
        export["evidence_steward"] = record["evidence_steward"]

    # confidence
    if record.get("confidence") is not None:
        export["confidence"] = record["confidence"]

    # assertion
    export["assertion"] = assertion

    # provenance
    if record.get("provenance"):
        export["provenance"] = record["provenance"]

    # evidence
    if evidence_list:
        export["evidence"] = evidence_list

    return export


def record_to_yaml(record: dict, decision: dict | None = None) -> str:
    """Convert a database record to YAML string.

    Args:
        record: Database record dict
        decision: Optional decision dict

    Returns:
        YAML string representation
    """
    export_dict = record_to_export_dict(record, decision)
    return yaml.dump(
        export_dict,
        default_flow_style=False,
        allow_unicode=True,
        sort_keys=False,
        width=120,
    )


def generate_export_records(
    db: CurationDatabase,
    statuses: list[str] | None = None,
) -> Generator[tuple[str, str, str], None, None]:
    """Generate exportable records as (filename, yaml_content, status) tuples.

    This is a generator to handle large numbers of records efficiently.

    Args:
        db: Database connection
        statuses: List of statuses to export (default: ACCEPTED, REJECTED, CONTROVERSIAL)

    Yields:
        Tuples of (filename, yaml_content, status)
    """
    if statuses is None:
        statuses = ["ACCEPTED", "REJECTED", "CONTROVERSIAL"]

    for status in statuses:
        records = db.get_records_by_status(status)

        for record in records:
            # Get the most recent decision
            decisions = db.get_decisions_for_record(record["id"])
            decision = decisions[0] if decisions else None

            # Generate YAML
            yaml_content = record_to_yaml(record, decision)

            # Generate safe filename from record ID
            record_id = record.get("id", "unknown")
            safe_id = (
                record_id.replace(":", "_")
                .replace("/", "_")
                .replace("\\", "_")
                .replace(" ", "_")
            )
            filename = f"{status.lower()}/{safe_id}.yaml"

            yield filename, yaml_content, status


def create_export_tarball(
    db: CurationDatabase,
    statuses: list[str] | None = None,
) -> bytes:
    """Create a tar.gz archive of all exportable records.

    Args:
        db: Database connection
        statuses: List of statuses to export (default: ACCEPTED, REJECTED, CONTROVERSIAL)

    Returns:
        Bytes of the tar.gz archive
    """
    buffer = io.BytesIO()

    with tarfile.open(fileobj=buffer, mode="w:gz") as tar:
        for filename, yaml_content, status in generate_export_records(db, statuses):
            # Create a TarInfo object for this file
            yaml_bytes = yaml_content.encode("utf-8")
            tarinfo = tarfile.TarInfo(name=filename)
            tarinfo.size = len(yaml_bytes)
            tarinfo.mtime = int(datetime.now().timestamp())

            # Add to archive
            tar.addfile(tarinfo, io.BytesIO(yaml_bytes))

    buffer.seek(0)
    return buffer.read()


def export_records_to_directory(
    db: CurationDatabase,
    output_dir: Path,
    statuses: list[str] | None = None,
) -> dict:
    """Export all records to a directory structure.

    Creates:
        output_dir/
            accepted/
                record1.yaml
                record2.yaml
            rejected/
                record3.yaml
            controversial/
                record4.yaml

    Args:
        db: Database connection
        output_dir: Base directory for export
        statuses: List of statuses to export

    Returns:
        Dict with counts per status
    """
    output_dir = Path(output_dir)
    counts = {"accepted": 0, "rejected": 0, "controversial": 0}

    for filename, yaml_content, status in generate_export_records(db, statuses):
        file_path = output_dir / filename
        file_path.parent.mkdir(parents=True, exist_ok=True)

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(yaml_content)

        counts[status.lower()] = counts.get(status.lower(), 0) + 1

    return counts
