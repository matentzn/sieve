"""Streamlit UI for the curation application."""

from datetime import datetime
from pathlib import Path
from uuid import uuid4

from dotenv import load_dotenv

load_dotenv(override=True)  # Load environment variables from .env file

import curies
import streamlit as st
import streamlit.components.v1 as components
import yaml

@st.cache_resource
def _get_obo_converter() -> curies.Converter:
    """Get the OBO converter, cached across Streamlit reruns."""
    return curies.get_obo_converter()


def expand_curie_to_link(curie: str) -> str:
    """Expand a CURIE to a clickable markdown link using OBO converter."""
    if not curie:
        return "?"

    converter = _get_obo_converter()
    expanded = converter.expand(curie)

    if expanded:
        return f"[`{curie}`]({expanded})"
    return f"`{curie}`"


def calculate_evidence_score(evidence: list[dict]) -> tuple[float, str]:
    """Calculate Net Evidence Ratio from evidence items.

    Formula: NER = (S+ - S-) / (S+ + S- + S?)
    Where:
    - S+ = sum of evidence_strength for SUPPORTS items
    - S- = sum of evidence_strength for CONTRADICTS items
    - S? = sum of evidence_strength for UNCERTAIN items

    Returns:
        Tuple of (score, formula_explanation)
        Score ranges from -1 (all contradicting) to +1 (all supporting)
    """
    if not evidence:
        return 0.0, "No evidence available"

    s_plus = 0.0  # Sum of supporting strengths
    s_minus = 0.0  # Sum of contradicting strengths
    s_uncertain = 0.0  # Sum of uncertain strengths

    for ev in evidence:
        strength = ev.get("evidence_strength", 1.0)
        direction = ev.get("direction", "SUPPORTS")

        if direction == "SUPPORTS":
            s_plus += strength
        elif direction == "CONTRADICTS":
            s_minus += strength
        else:  # UNCERTAIN
            s_uncertain += strength

    total = s_plus + s_minus + s_uncertain
    if total == 0:
        return 0.0, "No weighted evidence"

    score = (s_plus - s_minus) / total

    # Build formula explanation
    explanation = (
        f"**Net Evidence Ratio (NER)**\n\n"
        f"Formula: `(S+ - S-) / (S+ + S- + S?)`\n\n"
        f"Where:\n"
        f"- S+ (supporting) = {s_plus:.2f}\n"
        f"- S- (contradicting) = {s_minus:.2f}\n"
        f"- S? (uncertain) = {s_uncertain:.2f}\n\n"
        f"Calculation: `({s_plus:.2f} - {s_minus:.2f}) / ({s_plus:.2f} + {s_minus:.2f} + {s_uncertain:.2f})`\n\n"
        f"Result: **{score:.2f}**\n\n"
        f"Score ranges from -1 (all contradicting) to +1 (all supporting)"
    )

    return score, explanation


def render_mermaid(mermaid_code: str, height: int = 300):
    """Render a mermaid diagram using HTML component."""
    html = f"""
    <script src="https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"></script>
    <script>mermaid.initialize({{startOnLoad:true}});</script>
    <div class="mermaid">
    {mermaid_code}
    </div>
    """
    components.html(html, height=height)


def sanitize_mermaid_label(label: str) -> str:
    """Sanitize a label for use in mermaid diagrams."""
    return label.replace('"', "'").replace("(", "[").replace(")", "]").replace("<", "&lt;").replace(">", "&gt;")

from sieve.auth import get_curator_info, handle_oauth_callback, is_admin, is_authorized_curator, render_login_ui
from sieve.db import CurationDatabase
from sieve.export import export_accepted_records
from sieve.ingest import ingest_directory, parse_curation_record
from sieve.models import CurationDecision, DecisionType

# Page config
st.set_page_config(
    page_title="Sieve",
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

    # Handle OAuth callback if present
    handle_oauth_callback()

    # Sidebar navigation
    st.sidebar.title("🔬 Sieve")

    page = st.sidebar.radio(
        "Navigation",
        [
            "📋 Review Queue",
            "✅ Accepted",
            "❌ Rejected",
            "⚠️ Controversial",
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
    col1.metric("Unreviewed", stats["unreviewed"])
    col2.metric("Total", stats["total"])
    col1.metric("Accepted", stats["accepted"])
    col2.metric("Rejected", stats["rejected"])
    col1.metric("Controversial", stats["controversial"])

    # ORCID login/logout UI
    render_login_ui()

    # Route to page
    if page == "📋 Review Queue":
        render_review_queue()
    elif page == "✅ Accepted":
        render_status_list("ACCEPTED")
    elif page == "❌ Rejected":
        render_status_list("REJECTED")
    elif page == "⚠️ Controversial":
        render_status_list("CONTROVERSIAL")
    elif page == "📥 Ingest":
        render_ingest_page()
    elif page == "📤 Export":
        render_export_page()
    elif page == "📊 Dashboard":
        render_dashboard()


def render_review_queue():
    """Render the review queue page with paginated table."""
    st.title("📋 Review Queue")

    # Initialize session state for pagination and selection
    if "page_number" not in st.session_state:
        st.session_state.page_number = 0
    if "selected_record_id" not in st.session_state:
        st.session_state.selected_record_id = None
    if "sort_by" not in st.session_state:
        st.session_state.sort_by = "evidence_score"
    if "sort_order" not in st.session_state:
        st.session_state.sort_order = "ASC"

    # Page size
    page_size = 25

    # Sorting controls
    sort_col1, sort_col2 = st.columns([2, 1])
    with sort_col1:
        sort_options = {
            "Evidence Score": "evidence_score",
            "Date Added": "created_at",
            "Assertion": "assertion_display_text",
        }
        sort_label = st.selectbox(
            "Sort by",
            options=list(sort_options.keys()),
            index=0 if st.session_state.sort_by == "evidence_score" else 1,
        )
        st.session_state.sort_by = sort_options[sort_label]
    with sort_col2:
        order_options = {"Ascending": "ASC", "Descending": "DESC"}
        order_label = st.selectbox(
            "Order",
            options=list(order_options.keys()),
            index=0 if st.session_state.sort_order == "ASC" else 1,
        )
        st.session_state.sort_order = order_options[order_label]

    # Get paginated records
    offset = st.session_state.page_number * page_size
    records, total_count = db.get_records_paginated(
        status="UNREVIEWED",
        offset=offset,
        limit=page_size,
        sort_by=st.session_state.sort_by,
        sort_order=st.session_state.sort_order,
    )

    if total_count == 0:
        st.info("🎉 No unreviewed records! Ingest some files to get started.")
        return

    # Show count and pagination info
    total_pages = (total_count + page_size - 1) // page_size
    st.write(f"**{total_count} records pending review** (Page {st.session_state.page_number + 1} of {total_pages})")

    # Build table data
    table_data = []
    for r in records:
        display_text = r.get("assertion_display_text") or (
            f"{r.get('assertion_subject_label') or r.get('assertion_subject_id')} → "
            f"{r.get('assertion_object_label') or r.get('assertion_object_id')}"
        )
        predicate = r.get("assertion_predicate_label") or r.get("assertion_predicate", "")
        score = r.get("evidence_score")
        score_display = f"{score:+.2f}" if score is not None else "N/A"

        # Color indicator for score
        if score is not None:
            if score > 0.3:
                score_indicator = "🟢"
            elif score < -0.3:
                score_indicator = "🔴"
            else:
                score_indicator = "🟡"
        else:
            score_indicator = "⚪"

        table_data.append({
            "id": r["id"],
            "Score": f"{score_indicator} {score_display}",
            "Assertion": display_text[:80] + ("..." if len(display_text) > 80 else ""),
            "Predicate": predicate,
        })

    # Display as interactive dataframe
    import pandas as pd

    df = pd.DataFrame(table_data)

    # Use st.dataframe with selection
    selection = st.dataframe(
        df[["Score", "Assertion", "Predicate"]],
        width="stretch",
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row",
    )

    # Handle selection
    if selection and selection.selection and selection.selection.rows:
        selected_idx = selection.selection.rows[0]
        st.session_state.selected_record_id = table_data[selected_idx]["id"]

    # Pagination controls
    col1, col2, col3, col4, col5 = st.columns([1, 1, 2, 1, 1])
    with col1:
        if st.button("⏮️ First", disabled=st.session_state.page_number == 0):
            st.session_state.page_number = 0
            st.rerun()
    with col2:
        if st.button("◀️ Prev", disabled=st.session_state.page_number == 0):
            st.session_state.page_number -= 1
            st.rerun()
    with col3:
        # Page jump
        new_page = st.number_input(
            "Page",
            min_value=1,
            max_value=total_pages,
            value=st.session_state.page_number + 1,
            label_visibility="collapsed",
        )
        if new_page != st.session_state.page_number + 1:
            st.session_state.page_number = new_page - 1
            st.rerun()
    with col4:
        if st.button("Next ▶️", disabled=st.session_state.page_number >= total_pages - 1):
            st.session_state.page_number += 1
            st.rerun()
    with col5:
        if st.button("Last ⏭️", disabled=st.session_state.page_number >= total_pages - 1):
            st.session_state.page_number = total_pages - 1
            st.rerun()

    # Show review panel if record selected
    if st.session_state.selected_record_id:
        record = db.get_record(st.session_state.selected_record_id)
        if record:
            render_review_panel(record)


def render_review_panel(record: dict):
    """Render the review panel for a single record."""

    st.markdown("---")

    # Assertion display
    st.subheader("📝 Assertion")

    # Display text if available
    if record.get("assertion_display_text"):
        st.markdown(f"**{record['assertion_display_text']}**")

    # Render assertion as mermaid diagram
    subject_label = record.get("assertion_subject_label") or record["assertion_subject_id"]
    object_label = record.get("assertion_object_label") or record["assertion_object_id"]
    predicate_label = record.get("assertion_predicate_label") or record["assertion_predicate"]

    # Sanitize labels for mermaid (remove special characters)
    subject_label_safe = sanitize_mermaid_label(subject_label)
    object_label_safe = sanitize_mermaid_label(object_label)
    predicate_label_safe = sanitize_mermaid_label(predicate_label)

    mermaid_code = f"""graph LR
    S["{subject_label_safe}"] -->|{predicate_label_safe}| O["{object_label_safe}"]"""
    render_mermaid(mermaid_code, height=150)

    # Show IDs as clickable links
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"Subject: {expand_curie_to_link(record['assertion_subject_id'])}")
    with col2:
        st.markdown(f"Object: {expand_curie_to_link(record['assertion_object_id'])}")

    # Show last_updated if available
    if record.get("last_updated"):
        st.caption(f"Last updated: {record['last_updated']}")

    # Provenance
    provenance = record.get("provenance")
    if provenance:
        st.markdown("---")
        st.subheader("📜 Provenance")
        prov_cols = st.columns(3)
        with prov_cols[0]:
            attributed = provenance.get("attributed_to", [])
            if isinstance(attributed, list):
                attributed_str = ", ".join(attributed)
            else:
                attributed_str = attributed
            if attributed_str:
                st.markdown(f"**Attributed to:** {attributed_str}")
        with prov_cols[1]:
            if provenance.get("generated_at"):
                st.markdown(f"**Created:** {provenance['generated_at']}")
        with prov_cols[2]:
            if provenance.get("source_version"):
                st.markdown(f"**Source:** {provenance['source_version']}")

        # Display generated_by activity if present
        activity = provenance.get("generated_by")
        if activity:
            render_curation_activity(activity)

    # Evidence
    st.markdown("---")
    st.subheader("🔍 Evidence")

    evidence = record.get("evidence", [])

    if not evidence:
        st.warning("No evidence items provided for this assertion.")
    else:
        # Calculate and display evidence score
        score, formula_explanation = calculate_evidence_score(evidence)

        # Determine color based on score
        if score > 0.3:
            score_color = "green"
            score_label = "Supports"
        elif score < -0.3:
            score_color = "red"
            score_label = "Contradicts"
        else:
            score_color = "orange"
            score_label = "Mixed"

        # Display score with info popover
        score_col, info_col = st.columns([4, 1])
        with score_col:
            st.markdown(
                f"**Evidence Score:** :{score_color}[{score:+.2f}] ({score_label})"
            )
            # Visual indicator: progress bar centered at 0.5 (score of 0)
            # Map score from [-1, 1] to [0, 1] for display
            normalized_score = (score + 1) / 2
            st.progress(normalized_score)
        with info_col:
            with st.popover("❓"):
                st.markdown(formula_explanation)

        st.markdown(f"*{len(evidence)} evidence items*")

        # Render all evidence items
        for i, ev in enumerate(evidence):
            render_evidence_item(ev, i, record)

    # Decision section
    st.markdown("---")
    st.subheader("Your Decision")

    curator_orcid, _ = get_curator_info()
    if not curator_orcid:
        st.warning("Please log in with ORCID to make decisions.")
        return

    if not is_authorized_curator(curator_orcid):
        st.error("You are not authorized to make curation decisions. Contact an admin to be added to the curators list.")
        return

    # Certainty slider
    certainty = st.slider(
        "Certainty",
        min_value=0.0,
        max_value=1.0,
        value=0.8,
        step=0.1,
        help="How certain are you about this decision? (0 = uncertain, 1 = very certain)",
    )

    rationale = st.text_area(
        "Rationale (required for rejection)", placeholder="Explain your decision..."
    )

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        if st.button("Accept", type="primary", width="stretch"):
            make_decision(record["id"], "ACCEPT", rationale, certainty)
            st.rerun()

    with col2:
        if st.button("Reject", type="secondary", width="stretch"):
            if not rationale:
                st.error("Rationale is required for rejection.")
            else:
                make_decision(record["id"], "REJECT", rationale, certainty)
                st.rerun()

    with col3:
        if st.button("Controversial", width="stretch"):
            make_decision(record["id"], "CONTROVERSIAL", rationale, certainty)
            st.rerun()

    with col4:
        if st.button("Skip", width="stretch"):
            st.rerun()


def render_evidence_item(evidence: dict, index: int, record: dict = None):
    """Render a single evidence item."""

    ev_type = evidence.get("evidence_type", "OTHER")
    direction = evidence.get("direction", "SUPPORTS")

    # Icon mapping for evidence type
    type_icons = {
        "CONCORDANCE": "🔗",
        "LITERATURE": "📚",
        "EXPERT_REVIEW": "👨‍🔬",
        "COMPUTATIONAL": "🤖",
        "OTHER": "📌",
    }
    type_icon = type_icons.get(ev_type, "📌")

    # Icon and color for direction
    direction_indicators = {
        "SUPPORTS": ("✅", "green"),
        "CONTRADICTS": ("❌", "red"),
        "UNCERTAIN": ("❓", "orange"),
    }
    dir_icon, dir_color = direction_indicators.get(direction, ("❓", "gray"))

    # Evidence strength (default 1.0)
    strength = evidence.get("evidence_strength", 1.0)

    with st.expander(
        f"{type_icon} {dir_icon} **{ev_type}** — {evidence.get('description', 'No description')}",
        expanded=(index == 0),
    ):
        # Direction and strength indicators
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"**Direction:** :{dir_color}[{direction}]")
        with col2:
            st.markdown(f"**Strength:** {strength:.0%}")
            st.progress(strength)

        # ECO code
        if evidence.get("eco_code"):
            st.markdown(
                f"**Evidence type:** `{evidence['eco_code']}` ({evidence.get('eco_label', '')})"
            )

        # Type-specific rendering
        if ev_type == "CONCORDANCE":
            render_concordance_evidence(evidence, record)
        elif ev_type == "LITERATURE":
            render_literature_evidence(evidence)
        elif ev_type == "EXPERT_REVIEW":
            render_expert_review_evidence(evidence)
        elif ev_type == "COMPUTATIONAL":
            render_computational_evidence(evidence)
        else:
            st.json(evidence)


def render_concordance_evidence(evidence: dict, record: dict = None):
    """Render concordance evidence with mapping visualization."""

    # Source info
    source_name = evidence.get("source_name", "Unknown")
    source_type = evidence.get("source_type", "")
    source_uri = evidence.get("source")
    direction = evidence.get("direction", "SUPPORTS")

    if source_uri:
        st.markdown(f"**Source:** [{source_name}]({source_uri}) ({source_type})")
    else:
        st.markdown(f"**Source:** {source_name} ({source_type})")

    if evidence.get("mapping_set"):
        st.markdown(
            f"**Mapping set:** [{evidence['mapping_set']}]({evidence['mapping_set']})"
        )

    # Get Mondo assertion info from record
    mondo_subject_label = "?"
    mondo_object_label = "?"
    mondo_subject_id = "?"
    mondo_object_id = "?"
    mondo_predicate = "subClassOf"
    if record:
        mondo_subject_label = record.get("assertion_subject_label") or "?"
        mondo_object_label = record.get("assertion_object_label") or "?"
        mondo_subject_id = record.get("assertion_subject_id") or "?"
        mondo_object_id = record.get("assertion_object_id") or "?"
        mondo_predicate = record.get("assertion_predicate_label") or record.get("assertion_predicate") or "subClassOf"

    # Get source assertion info
    source_subject_label = evidence.get("source_subject_label") or "?"
    source_object_label = evidence.get("source_object_label") or "?"
    source_subject_id = evidence.get("source_subject_id") or "?"
    source_object_id = evidence.get("source_object_id") or "?"
    source_predicate = evidence.get("predicate_label") or evidence.get("predicate_id") or "subClassOf"

    # Build display strings with label and ID
    mondo_subject_display = f"{mondo_subject_label} [{mondo_subject_id}]" if mondo_subject_label != "?" else mondo_subject_id
    mondo_object_display = f"{mondo_object_label} [{mondo_object_id}]" if mondo_object_label != "?" else mondo_object_id
    source_subject_display = f"{source_subject_label} [{source_subject_id}]" if source_subject_label != "?" else source_subject_id
    source_object_display = f"{source_object_label} [{source_object_id}]" if source_object_label != "?" else source_object_id

    # Sanitize labels for mermaid
    mondo_subject_safe = sanitize_mermaid_label(mondo_subject_display)
    mondo_object_safe = sanitize_mermaid_label(mondo_object_display)
    mondo_predicate_safe = sanitize_mermaid_label(mondo_predicate)
    source_subject_safe = sanitize_mermaid_label(source_subject_display)
    source_object_safe = sanitize_mermaid_label(source_object_display)
    source_predicate_safe = sanitize_mermaid_label(source_predicate)
    source_name_safe = source_name.replace(" ", "_").replace("-", "_")

    # Render mermaid diagram showing both assertions and mappings
    # For SUPPORTS: show the relationship exists in source
    # For CONTRADICTS: show the relationship is ABSENT in source (no edge, just nodes with mappings)
    if direction == "CONTRADICTS":
        # Source has mappings but NO relationship between the terms
        mermaid_code = f"""graph LR
    subgraph Mondo["Mondo Assertion"]
        direction BT
        MS["{mondo_subject_safe}"] -->|{mondo_predicate_safe}| MO["{mondo_object_safe}"]
    end
    subgraph Source["{source_name_safe} - no relationship"]
        direction BT
        SS["{source_subject_safe}"]
        SO["{source_object_safe}"]
    end
    MS <-.->|mapping| SS
    MO <-.->|mapping| SO"""
    else:
        # SUPPORTS or UNCERTAIN: show the relationship exists in source
        mermaid_code = f"""graph LR
    subgraph Mondo["Mondo Assertion"]
        direction BT
        MS["{mondo_subject_safe}"] -->|{mondo_predicate_safe}| MO["{mondo_object_safe}"]
    end
    subgraph Source["{source_name_safe}"]
        direction BT
        SS["{source_subject_safe}"] -->|{source_predicate_safe}| SO["{source_object_safe}"]
    end
    MS <-.->|mapping| SS
    MO <-.->|mapping| SO"""
    render_mermaid(mermaid_code, height=450)

    # Show IDs as clickable links
    st.markdown("**Identifiers:**")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**Mondo:**")
        if record:
            st.markdown(f"Subject: {expand_curie_to_link(record.get('assertion_subject_id'))}")
            st.markdown(f"Object: {expand_curie_to_link(record.get('assertion_object_id'))}")
    with col2:
        st.markdown(f"**{source_name}:**")
        st.markdown(f"Subject: {expand_curie_to_link(evidence.get('source_subject_id'))}")
        st.markdown(f"Object: {expand_curie_to_link(evidence.get('source_object_id'))}")


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

    if evidence.get("explanation"):
        st.markdown("**Explanation:**")
        st.markdown(f"_{evidence['explanation']}_")


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

    if evidence.get("issue"):
        issue_url = evidence["issue"]
        st.markdown(f"**Issue:** [{issue_url}]({issue_url})")


def render_computational_evidence(evidence: dict):
    """Render computational evidence."""

    if evidence.get("method"):
        st.markdown(f"**Method:** {evidence['method']}")

    if evidence.get("method_uri"):
        st.markdown(f"**Method URI:** [{evidence['method_uri']}]({evidence['method_uri']})")

    if evidence.get("confidence_score") is not None:
        score = evidence["confidence_score"]
        st.markdown(f"**Confidence score:** {score:.2f}")
        st.progress(min(1.0, max(0.0, score)))

    if evidence.get("parameters"):
        st.markdown("**Parameters:**")
        st.code(evidence["parameters"], language=None)


def render_curation_activity(activity: dict):
    """Render a curation activity."""

    with st.expander("📋 **Curation Activity**", expanded=False):
        if activity.get("description"):
            st.markdown(f"**Description:** {activity['description']}")

        col1, col2 = st.columns(2)
        with col1:
            if activity.get("started_at"):
                st.markdown(f"**Started:** {activity['started_at']}")
            if activity.get("ended_at"):
                st.markdown(f"**Ended:** {activity['ended_at']}")

        with col2:
            if activity.get("created_with"):
                st.markdown(f"**Tool:** [{activity['created_with']}]({activity['created_with']})")

        if activity.get("associated_with"):
            associated = activity["associated_with"]
            if isinstance(associated, list):
                links = []
                for a in associated:
                    if "orcid.org" in a or a.startswith("orcid:"):
                        orcid = a.replace("orcid:", "")
                        links.append(f"[{orcid}](https://orcid.org/{orcid})")
                    else:
                        links.append(f"[{a}]({a})")
                st.markdown(f"**Associated with:** {', '.join(links)}")
            else:
                st.markdown(f"**Associated with:** {associated}")

        if activity.get("pull_request"):
            pr_url = activity["pull_request"]
            st.markdown(f"**Pull request:** [{pr_url}]({pr_url})")


def make_decision(record_id: str, decision: str, rationale: str, certainty: float = 1.0):
    """Record a curation decision."""
    curator_orcid, curator_name = get_curator_info()

    if not curator_orcid:
        st.error("Please log in with ORCID to make decisions.")
        return

    if not is_authorized_curator(curator_orcid):
        st.error("You are not authorized to make curation decisions.")
        return

    decision_obj = CurationDecision(
        id=f"decision:{uuid4().hex[:12]}",
        record_id=record_id,
        curator_orcid=curator_orcid,
        curator_name=curator_name,
        decision=DecisionType(decision),
        certainty=certainty,
        rationale=rationale if rationale else None,
        decided_at=datetime.now(),
    )

    db.record_decision(decision_obj)
    st.success(f"Decision recorded: {decision}")


def render_status_list(status: str):
    """Render paginated list of records with given status."""
    title_map = {
        "ACCEPTED": "Accepted",
        "REJECTED": "Rejected",
        "CONTROVERSIAL": "Controversial",
    }
    st.title(title_map.get(status, status))

    # Session state keys for this status
    page_key = f"{status.lower()}_page"
    selected_key = f"{status.lower()}_selected"
    sort_by_key = f"{status.lower()}_sort_by"
    sort_order_key = f"{status.lower()}_sort_order"

    # Initialize session state
    if page_key not in st.session_state:
        st.session_state[page_key] = 0
    if selected_key not in st.session_state:
        st.session_state[selected_key] = None
    if sort_by_key not in st.session_state:
        st.session_state[sort_by_key] = "decided_at"
    if sort_order_key not in st.session_state:
        st.session_state[sort_order_key] = "DESC"

    page_size = 25

    # Sorting controls
    sort_col1, sort_col2 = st.columns([2, 1])
    with sort_col1:
        sort_options = {
            "Decision Date": "decided_at",
            "Evidence Score": "evidence_score",
            "Certainty": "certainty",
            "Assertion": "assertion_display_text",
            "Curator": "curator_name",
        }
        current_sort = st.session_state[sort_by_key]
        current_label = next((k for k, v in sort_options.items() if v == current_sort), "Decision Date")
        sort_label = st.selectbox(
            "Sort by",
            options=list(sort_options.keys()),
            index=list(sort_options.keys()).index(current_label),
            key=f"{status}_sort_select",
        )
        st.session_state[sort_by_key] = sort_options[sort_label]
    with sort_col2:
        order_options = {"Newest First": "DESC", "Oldest First": "ASC"}
        current_order = st.session_state[sort_order_key]
        current_order_label = "Newest First" if current_order == "DESC" else "Oldest First"
        order_label = st.selectbox(
            "Order",
            options=list(order_options.keys()),
            index=list(order_options.keys()).index(current_order_label),
            key=f"{status}_order_select",
        )
        st.session_state[sort_order_key] = order_options[order_label]

    # Get paginated records with decision info
    offset = st.session_state[page_key] * page_size
    records, total_count = db.get_records_with_decisions_paginated(
        status=status,
        offset=offset,
        limit=page_size,
        sort_by=st.session_state[sort_by_key],
        sort_order=st.session_state[sort_order_key],
    )

    if total_count == 0:
        st.info(f"No {status.lower()} records.")
        return

    # Show count and pagination info
    total_pages = (total_count + page_size - 1) // page_size
    st.write(f"**{total_count} records** (Page {st.session_state[page_key] + 1} of {total_pages})")

    # Build table data
    import pandas as pd

    table_data = []
    for r in records:
        display_text = r.get("assertion_display_text") or (
            f"{r.get('assertion_subject_label') or r.get('assertion_subject_id')} -> "
            f"{r.get('assertion_object_label') or r.get('assertion_object_id')}"
        )
        score = r.get("evidence_score")
        score_display = f"{score:+.2f}" if score is not None else "N/A"

        # Curator info
        curator = r.get("curator_name") or r.get("curator_orcid") or "Unknown"

        # Decision date
        decided_at = r.get("decided_at")
        date_display = str(decided_at)[:10] if decided_at else "N/A"

        # Certainty
        certainty = r.get("certainty")
        certainty_display = f"{certainty:.0%}" if certainty is not None else "N/A"

        table_data.append({
            "id": r["id"],
            "Assertion": display_text[:60] + ("..." if len(display_text) > 60 else ""),
            "Score": score_display,
            "Certainty": certainty_display,
            "Decided By": curator[:20] + ("..." if len(curator) > 20 else ""),
            "Date": date_display,
        })

    df = pd.DataFrame(table_data)

    # Display as interactive dataframe
    selection = st.dataframe(
        df[["Assertion", "Score", "Certainty", "Decided By", "Date"]],
        width="stretch",
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row",
    )

    # Handle selection
    if selection and selection.selection and selection.selection.rows:
        selected_idx = selection.selection.rows[0]
        st.session_state[selected_key] = table_data[selected_idx]["id"]

    # Pagination controls
    col1, col2, col3, col4, col5 = st.columns([1, 1, 2, 1, 1])
    with col1:
        if st.button("First", disabled=st.session_state[page_key] == 0, key=f"{status}_first"):
            st.session_state[page_key] = 0
            st.rerun()
    with col2:
        if st.button("Prev", disabled=st.session_state[page_key] == 0, key=f"{status}_prev"):
            st.session_state[page_key] -= 1
            st.rerun()
    with col3:
        new_page = st.number_input(
            "Page",
            min_value=1,
            max_value=total_pages,
            value=st.session_state[page_key] + 1,
            label_visibility="collapsed",
            key=f"{status}_page_input",
        )
        if new_page != st.session_state[page_key] + 1:
            st.session_state[page_key] = new_page - 1
            st.rerun()
    with col4:
        if st.button("Next", disabled=st.session_state[page_key] >= total_pages - 1, key=f"{status}_next"):
            st.session_state[page_key] += 1
            st.rerun()
    with col5:
        if st.button("Last", disabled=st.session_state[page_key] >= total_pages - 1, key=f"{status}_last"):
            st.session_state[page_key] = total_pages - 1
            st.rerun()

    # Show detail panel if record selected
    if st.session_state[selected_key]:
        render_decided_record_panel(st.session_state[selected_key], status)


def render_decided_record_panel(record_id: str, status: str):
    """Render detail panel for a decided record."""
    record = db.get_record(record_id)
    if not record:
        st.error("Record not found")
        return

    st.markdown("---")

    # Record status info
    st.subheader("Record Status")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f"**Status:** {record.get('status', 'N/A')}")
    with col2:
        steward = record.get("evidence_steward")
        if steward:
            steward_display = steward.replace("orcid:", "") if steward.startswith("orcid:") else steward
            st.markdown(f"**Evidence Steward:** [{steward_display}](https://orcid.org/{steward_display})")
        else:
            st.markdown("**Evidence Steward:** N/A")
    with col3:
        confidence = record.get("confidence")
        confidence_display = f"{confidence:.0%}" if confidence is not None else "N/A"
        st.markdown(f"**Confidence:** {confidence_display}")

    # Decision history
    decisions = db.get_decisions_for_record(record_id)
    if decisions:
        d = decisions[0]
        st.subheader("Latest Decision")
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            curator = d.get("curator_name") or d.get("curator_orcid", "Unknown")
            st.markdown(f"**Decided by:** {curator}")
        with col2:
            st.markdown(f"**Date:** {d.get('decided_at', 'N/A')}")
        with col3:
            st.markdown(f"**Decision:** {d.get('decision', status)}")
        with col4:
            certainty = d.get("certainty")
            certainty_display = f"{certainty:.0%}" if certainty is not None else "N/A"
            st.markdown(f"**Certainty:** {certainty_display}")

        if d.get("rationale"):
            st.markdown(f"**Rationale:** {d['rationale']}")

    # Assertion display
    st.subheader("Assertion")

    if record.get("assertion_display_text"):
        st.markdown(f"**{record['assertion_display_text']}**")

    # Render assertion as mermaid diagram
    subject_label = record.get("assertion_subject_label") or record["assertion_subject_id"]
    object_label = record.get("assertion_object_label") or record["assertion_object_id"]
    predicate_label = record.get("assertion_predicate_label") or record["assertion_predicate"]

    subject_label_safe = sanitize_mermaid_label(subject_label)
    object_label_safe = sanitize_mermaid_label(object_label)
    predicate_label_safe = sanitize_mermaid_label(predicate_label)

    mermaid_code = f"""graph LR
    S["{subject_label_safe}"] -->|{predicate_label_safe}| O["{object_label_safe}"]"""
    render_mermaid(mermaid_code, height=150)

    # Show IDs as clickable links
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"Subject: {expand_curie_to_link(record['assertion_subject_id'])}")
    with col2:
        st.markdown(f"Object: {expand_curie_to_link(record['assertion_object_id'])}")

    # Evidence section
    st.markdown("---")
    st.subheader("Evidence")

    evidence = record.get("evidence", [])
    if not evidence:
        st.warning("No evidence items provided for this assertion.")
    else:
        # Calculate and display evidence score
        score, formula_explanation = calculate_evidence_score(evidence)

        if score > 0.3:
            score_color = "green"
            score_label = "Supports"
        elif score < -0.3:
            score_color = "red"
            score_label = "Contradicts"
        else:
            score_color = "orange"
            score_label = "Mixed"

        score_col, info_col = st.columns([4, 1])
        with score_col:
            st.markdown(f"**Evidence Score:** :{score_color}[{score:+.2f}] ({score_label})")
            normalized_score = (score + 1) / 2
            st.progress(normalized_score)
        with info_col:
            with st.popover("?"):
                st.markdown(formula_explanation)

        st.markdown(f"*{len(evidence)} evidence items*")

        for i, ev in enumerate(evidence):
            render_evidence_item(ev, i, record)

    # Admin: Return to queue button
    st.markdown("---")
    curator_orcid, _ = get_curator_info()
    if curator_orcid and is_admin(curator_orcid):
        if st.button("Return to Queue", type="secondary", key=f"return_{record_id}"):
            db.return_to_queue(record_id)
            st.session_state[f"{status.lower()}_selected"] = None
            st.success("Record returned to review queue")
            st.rerun()
    elif curator_orcid and is_authorized_curator(curator_orcid):
        st.caption("Only admins can return records to the queue.")


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
evidence:
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
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Total Records", stats["total"])
    col2.metric("Unreviewed", stats["unreviewed"], delta=None)
    col3.metric("Accepted", stats["accepted"])
    col4.metric("Rejected", stats["rejected"])
    col5.metric("Controversial", stats["controversial"])

    # Progress
    if stats["total"] > 0:
        reviewed = stats["accepted"] + stats["rejected"] + stats["controversial"]
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
            "UNREVIEWED": "⏳",
            "ACCEPTED": "✅",
            "REJECTED": "❌",
            "CONTROVERSIAL": "⚠️",
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
