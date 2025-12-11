"""Streamlit UI for the curation application."""

from datetime import datetime
from pathlib import Path
from uuid import uuid4

import streamlit as st
import yaml

from sieve.db import CurationDatabase
from sieve.export import export_accepted_records
from sieve.ingest import ingest_directory, parse_curation_record
from sieve.models import CurationDecision, DecisionType

# Page config
st.set_page_config(
    page_title="Curation App",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded",
)


# Initialize database
@st.cache_resource
def get_db():
    return CurationDatabase("data/curation.duckdb")


db = get_db()


def main():
    """Main application entry point."""

    # Sidebar navigation
    st.sidebar.title("🔬 Curation App")

    page = st.sidebar.radio(
        "Navigation",
        [
            "📋 Review Queue",
            "✅ Accepted",
            "❌ Rejected",
            "📥 Ingest",
            "📤 Export",
            "📊 Dashboard",
        ],
    )

    # Stats in sidebar
    stats = db.get_stats()
    st.sidebar.markdown("---")
    st.sidebar.markdown("### Statistics")
    col1, col2 = st.sidebar.columns(2)
    col1.metric("Pending", stats["pending"])
    col2.metric("Total", stats["total"])
    col1.metric("Accepted", stats["accepted"])
    col2.metric("Rejected", stats["rejected"])

    # Curator info
    st.sidebar.markdown("---")
    curator_orcid = st.sidebar.text_input(
        "Your ORCID",
        value=st.session_state.get("curator_orcid", ""),
        placeholder="0000-0000-0000-0000",
    )
    curator_name = st.sidebar.text_input(
        "Your Name",
        value=st.session_state.get("curator_name", ""),
        placeholder="Dr. Jane Smith",
    )
    st.session_state["curator_orcid"] = curator_orcid
    st.session_state["curator_name"] = curator_name

    # Route to page
    if page == "📋 Review Queue":
        render_review_queue()
    elif page == "✅ Accepted":
        render_status_list("ACCEPTED")
    elif page == "❌ Rejected":
        render_status_list("REJECTED")
    elif page == "📥 Ingest":
        render_ingest_page()
    elif page == "📤 Export":
        render_export_page()
    elif page == "📊 Dashboard":
        render_dashboard()


def render_review_queue():
    """Render the review queue page."""
    st.title("📋 Review Queue")

    pending_records = db.get_records_by_status("PENDING")

    if not pending_records:
        st.info("🎉 No pending records to review! Ingest some files to get started.")
        return

    st.write(f"**{len(pending_records)} records pending review**")

    # Record selection
    record_options = {
        f"{r['assertion_subject_label'] or r['assertion_subject_id']} → {r['assertion_object_label'] or r['assertion_object_id']}": r[
            "id"
        ]
        for r in pending_records
    }

    selected_label = st.selectbox(
        "Select a record to review", options=list(record_options.keys())
    )

    if selected_label:
        record_id = record_options[selected_label]
        record = db.get_record(record_id)
        render_review_panel(record)


def render_review_panel(record: dict):
    """Render the review panel for a single record."""

    st.markdown("---")

    # Assertion display
    st.subheader("📝 Assertion")

    col1, col2, col3 = st.columns([2, 1, 2])

    with col1:
        st.markdown(f"### {record['assertion_subject_label'] or 'No label'}")
        st.code(record["assertion_subject_id"], language=None)

    with col2:
        st.markdown("### →")
        predicate_label = (
            record.get("assertion_predicate_label") or record["assertion_predicate"]
        )
        st.markdown(f"**{predicate_label}**")

    with col3:
        st.markdown(f"### {record['assertion_object_label'] or 'No label'}")
        st.code(record["assertion_object_id"], language=None)

    # Provenance
    if record.get("provenance_attributed_to"):
        st.markdown("---")
        st.subheader("📜 Provenance")
        prov_cols = st.columns(3)
        with prov_cols[0]:
            st.markdown(
                f"**Attributed to:** {record.get('provenance_attributed_to_label', record['provenance_attributed_to'])}"
            )
        with prov_cols[1]:
            if record.get("provenance_generated_at"):
                st.markdown(f"**Created:** {record['provenance_generated_at']}")
        with prov_cols[2]:
            if record.get("provenance_source_version"):
                st.markdown(f"**Source:** {record['provenance_source_version']}")

    # Evidence
    st.markdown("---")
    st.subheader("🔍 Supporting Evidence")

    evidence_items = record.get("evidence_items", [])

    if not evidence_items:
        st.warning("No evidence items provided for this assertion.")
    else:
        for i, ev in enumerate(evidence_items):
            render_evidence_item(ev, i)

    # Decision section
    st.markdown("---")
    st.subheader("⚖️ Your Decision")

    if not st.session_state.get("curator_orcid"):
        st.warning("Please enter your ORCID in the sidebar before making decisions.")
        return

    rationale = st.text_area(
        "Rationale (required for rejection)", placeholder="Explain your decision..."
    )

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        if st.button("✅ Accept", type="primary", use_container_width=True):
            make_decision(record["id"], "ACCEPT", rationale)
            st.rerun()

    with col2:
        if st.button("❌ Reject", type="secondary", use_container_width=True):
            if not rationale:
                st.error("Rationale is required for rejection.")
            else:
                make_decision(record["id"], "REJECT", rationale)
                st.rerun()

    with col3:
        if st.button("⏸️ Defer", use_container_width=True):
            make_decision(record["id"], "DEFER", rationale)
            st.rerun()

    with col4:
        if st.button("⏭️ Skip", use_container_width=True):
            st.rerun()


def render_evidence_item(evidence: dict, index: int):
    """Render a single evidence item."""

    ev_type = evidence.get("evidence_type", "OTHER")

    # Icon mapping
    icons = {
        "CONCORDANCE": "🔗",
        "LITERATURE": "📚",
        "EXPERT_REVIEW": "👨‍🔬",
        "COMPUTATIONAL": "🤖",
        "OTHER": "📌",
    }
    icon = icons.get(ev_type, "📌")

    with st.expander(
        f"{icon} **{ev_type}** — {evidence.get('description', 'No description')}",
        expanded=(index == 0),
    ):
        # ECO code
        if evidence.get("eco_code"):
            st.markdown(
                f"**Evidence type:** `{evidence['eco_code']}` ({evidence.get('eco_label', '')})"
            )

        # Type-specific rendering
        if ev_type == "CONCORDANCE":
            render_concordance_evidence(evidence)
        elif ev_type == "LITERATURE":
            render_literature_evidence(evidence)
        elif ev_type == "EXPERT_REVIEW":
            render_expert_review_evidence(evidence)
        else:
            st.json(evidence)


def render_concordance_evidence(evidence: dict):
    """Render concordance evidence with mapping visualization."""

    st.markdown(f"**Source ontology:** {evidence.get('source_ontology', 'Unknown')}")

    if evidence.get("mapping_set_uri"):
        st.markdown(
            f"**Mapping set:** [{evidence['mapping_set_uri']}]({evidence['mapping_set_uri']})"
        )

    # Visual mapping display
    st.markdown("#### Mapping Chain")

    col1, col2, col3 = st.columns([2, 1, 2])

    with col1:
        st.markdown("**Subject mapping:**")
        if evidence.get("source_subject_id"):
            st.code(
                f"→ {evidence['source_subject_label'] or evidence['source_subject_id']}",
                language=None,
            )

    with col2:
        st.markdown("**↓**")

    with col3:
        st.markdown("**Object mapping:**")
        if evidence.get("source_object_id"):
            st.code(
                f"→ {evidence['source_object_label'] or evidence['source_object_id']}",
                language=None,
            )


def render_literature_evidence(evidence: dict):
    """Render literature evidence with quote."""

    if evidence.get("publication_id"):
        pub_id = evidence["publication_id"]
        if pub_id.startswith("PMID:"):
            pmid = pub_id.replace("PMID:", "")
            st.markdown(
                f"**Publication:** [{evidence.get('publication_title', pub_id)}](https://pubmed.ncbi.nlm.nih.gov/{pmid})"
            )
        else:
            st.markdown(
                f"**Publication:** {evidence.get('publication_title', pub_id)}"
            )

    if evidence.get("quoted_text"):
        st.markdown("**Quoted text:**")
        st.info(f'"{evidence["quoted_text"]}"')

        if evidence.get("quote_location"):
            st.caption(f"📍 {evidence['quote_location']}")


def render_expert_review_evidence(evidence: dict):
    """Render expert review evidence."""

    reviewer_info = []
    if evidence.get("reviewer_name"):
        reviewer_info.append(evidence["reviewer_name"])
    if evidence.get("reviewer_affiliation"):
        reviewer_info.append(evidence["reviewer_affiliation"])

    if reviewer_info:
        st.markdown(f"**Reviewer:** {', '.join(reviewer_info)}")

    if evidence.get("reviewer_orcid"):
        orcid = evidence["reviewer_orcid"].replace("orcid:", "")
        st.markdown(f"**ORCID:** [{orcid}](https://orcid.org/{orcid})")

    if evidence.get("reviewed_at"):
        st.markdown(f"**Reviewed:** {evidence['reviewed_at']}")


def make_decision(record_id: str, decision: str, rationale: str):
    """Record a curation decision."""

    decision_obj = CurationDecision(
        id=f"decision:{uuid4().hex[:12]}",
        record_id=record_id,
        curator_orcid=f"orcid:{st.session_state['curator_orcid']}",
        curator_name=st.session_state.get("curator_name"),
        decision=DecisionType(decision),
        rationale=rationale if rationale else None,
        decided_at=datetime.now(),
    )

    db.record_decision(decision_obj)
    st.success(f"Decision recorded: {decision}")


def render_status_list(status: str):
    """Render list of records with given status."""
    title_map = {
        "ACCEPTED": "✅ Accepted",
        "REJECTED": "❌ Rejected",
        "DEFERRED": "⏸️ Deferred",
    }
    st.title(title_map.get(status, status))

    records = db.get_records_by_status(status)

    if not records:
        st.info(f"No {status.lower()} records.")
        return

    st.write(f"**{len(records)} records**")

    for record in records:
        with st.expander(
            f"{record['assertion_subject_label'] or record['assertion_subject_id']} → "
            f"{record['assertion_object_label'] or record['assertion_object_id']}"
        ):
            st.code(
                f"{record['assertion_subject_id']} {record['assertion_predicate']} {record['assertion_object_id']}",
                language=None,
            )

            # Show decision info
            decisions = db.get_decisions_for_record(record["id"])
            if decisions:
                d = decisions[0]
                st.markdown(
                    f"**Decided by:** {d.get('curator_name', d['curator_orcid'])}"
                )
                st.markdown(f"**Date:** {d['decided_at']}")
                if d.get("rationale"):
                    st.markdown(f"**Rationale:** {d['rationale']}")


def render_ingest_page():
    """Render the file ingestion page."""
    st.title("📥 Ingest Records")

    tab1, tab2 = st.tabs(["📁 From Directory", "📝 Paste YAML"])

    with tab1:
        st.markdown("Ingest YAML files from the `inbox/` directory.")

        inbox_path = st.text_input("Inbox path", value="inbox/")

        if st.button("🔄 Scan & Ingest", type="primary"):
            with st.spinner("Ingesting files..."):
                stats = ingest_directory(Path(inbox_path), db)

            if stats["success"] > 0:
                st.success(f"✅ Ingested {stats['success']} new records")
            if stats["skipped"] > 0:
                st.info(f"⏭️ Skipped {stats['skipped']} existing records")
            if stats["errors"] > 0:
                st.error(f"❌ {stats['errors']} errors")
                for err in stats.get("error_details", []):
                    st.code(f"{err['file']}: {err['error']}")

    with tab2:
        st.markdown("Paste a YAML record directly.")

        yaml_content = st.text_area(
            "YAML content",
            height=400,
            placeholder="""id: example-001
assertion:
  subject_id: MONDO:0005015
  subject_label: diabetes mellitus
  predicate: rdfs:subClassOf
  object_id: MONDO:0005151
  object_label: endocrine system disorder
evidence_items:
  - evidence_type: LITERATURE
    publication_id: PMID:12345
    quoted_text: "Example supporting text..."
""",
        )

        if st.button("📥 Ingest YAML"):
            if yaml_content:
                try:
                    data = yaml.safe_load(yaml_content)
                    record = parse_curation_record(data)

                    if db.record_exists(record.id):
                        st.warning(f"Record {record.id} already exists.")
                    else:
                        db.insert_record(record)
                        st.success(f"✅ Ingested record: {record.id}")
                except Exception as e:
                    st.error(f"Error: {e}")


def render_export_page():
    """Render the export page."""
    st.title("📤 Export Accepted Records")

    stats = db.get_stats()
    st.write(f"**{stats['accepted']} accepted records** ready for export")

    if stats["accepted"] == 0:
        st.info("No accepted records to export. Review some records first!")
        return

    col1, col2 = st.columns(2)

    with col1:
        export_format = st.selectbox(
            "Output format", options=["turtle", "xml", "json-ld", "n3"], index=0
        )

    with col2:
        include_provenance = st.checkbox("Include curation provenance", value=True)

    if st.button("📤 Generate Export", type="primary"):
        with st.spinner("Generating RDF export..."):
            output_path = export_accepted_records(
                db,
                Path("data/exports"),
                format=export_format,
                include_provenance=include_provenance,
            )

        st.success(f"✅ Export saved to: `{output_path}`")

        # Show preview
        with open(output_path, "r") as f:
            content = f.read()

        st.markdown("### Preview")
        st.code(
            content[:2000] + ("..." if len(content) > 2000 else ""), language="turtle"
        )

        # Download button
        st.download_button(
            label="⬇️ Download",
            data=content,
            file_name=output_path.name,
            mime="text/turtle",
        )


def render_dashboard():
    """Render the dashboard page."""
    st.title("📊 Dashboard")

    stats = db.get_stats()

    # Metrics row
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Records", stats["total"])
    col2.metric("Pending", stats["pending"], delta=None)
    col3.metric("Accepted", stats["accepted"])
    col4.metric("Rejected", stats["rejected"])

    # Progress
    if stats["total"] > 0:
        reviewed = stats["accepted"] + stats["rejected"]
        progress = reviewed / stats["total"]
        st.progress(
            progress, text=f"{reviewed}/{stats['total']} reviewed ({progress*100:.0f}%)"
        )

    # Recent activity
    st.markdown("---")
    st.subheader("Recent Records")

    records = db.get_all_records()[:10]

    for r in records:
        status_emoji = {
            "PENDING": "⏳",
            "ACCEPTED": "✅",
            "REJECTED": "❌",
            "DEFERRED": "⏸️",
        }
        emoji = status_emoji.get(r["status"], "❓")

        st.markdown(
            f"{emoji} **{r['assertion_subject_label'] or r['assertion_subject_id']}** → "
            f"{r['assertion_object_label'] or r['assertion_object_id']} "
            f"({r['status']})"
        )


if __name__ == "__main__":
    main()


def run():
    """Entry point for the application."""
    main()
