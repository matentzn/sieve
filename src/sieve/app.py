"""Streamlit UI for curating SEPIO EvidencePackets."""

from datetime import datetime
from uuid import uuid4

import streamlit as st
from dotenv import load_dotenv

from sieve.auth import (
    get_curator_info,
    handle_oauth_callback,
    is_authorized_curator,
    render_login_ui,
)
from sieve.datamodel import CurationDecision, DecisionType, EvidencePacket
from sieve.scoring import net_evidence_ratio
from sieve.store import PacketStore

load_dotenv(override=True)

DB_PATH = "data/sieve.duckdb"

st.set_page_config(page_title="Sieve", page_icon="🔬", layout="wide")


@st.cache_resource
def get_store() -> PacketStore:
    """Return a cached PacketStore."""
    return PacketStore(DB_PATH)


def _predicate_label(packet: EvidencePacket) -> str:
    stmt = packet.statement
    if stmt and stmt.predicate:
        return getattr(stmt.predicate, "label", None) or getattr(stmt.predicate, "code", "") or ""
    return ""


def main() -> None:
    """Entry point for the Streamlit app."""
    handle_oauth_callback()
    store = get_store()

    st.sidebar.title("🔬 Sieve")
    page = st.sidebar.radio(
        "Navigate",
        ["Dashboard", "Review Queue", "Ingest", "Export"],
    )

    st.sidebar.markdown("---")
    st.sidebar.markdown("### Statistics")
    for status, count in sorted(store.get_stats().items()):
        st.sidebar.write(f"**{status}**: {count}")

    st.sidebar.markdown("---")
    render_login_ui()

    if page == "Dashboard":
        render_dashboard(store)
    elif page == "Review Queue":
        render_review_queue(store)
    elif page == "Ingest":
        render_ingest(store)
    elif page == "Export":
        render_export(store)


def render_dashboard(store: PacketStore) -> None:
    """Show summary statistics."""
    st.title("Dashboard")
    stats = store.get_stats()
    total = sum(stats.values())
    st.metric("Total packets", total)
    cols = st.columns(max(len(stats), 1))
    for col, (status, count) in zip(cols, sorted(stats.items())):
        col.metric(status, count)


def render_review_queue(store: PacketStore) -> None:
    """List packets by status and open one for review."""
    st.title("Review Queue")
    status = st.selectbox(
        "Status", ["UNREVIEWED", "ACCEPTED", "REJECTED", "CONTROVERSIAL"]
    )
    rows = store.list_packets(status=status)
    if not rows:
        st.info(f"No packets with status {status}.")
        return

    labels = {
        f"{r['id']}  ·  {r['subject_id']} → {r['object_id']}  (NER {r['evidence_score']:.2f})": r["id"]
        for r in rows
    }
    choice = st.selectbox("Packet", list(labels.keys()))
    if choice:
        render_packet_detail(store, labels[choice])


def render_packet_detail(store: PacketStore, packet_id: str) -> None:
    """Render one packet: statement, evidence lines, decisions."""
    packet = store.get_packet(packet_id)
    if packet is None:
        st.error("Packet not found.")
        return

    stmt = packet.statement
    st.header(getattr(stmt, "statement_text", None) or packet_id)
    st.write(
        f"**{getattr(stmt, 'subject_label', '') or getattr(stmt, 'subject', '')}** "
        f"*{_predicate_label(packet)}* "
        f"**{getattr(stmt, 'object_label', '') or getattr(stmt, 'object', '')}**"
    )
    st.write(f"Status: `{packet.status}`  ·  NER: `{net_evidence_ratio(packet):.2f}`")

    st.subheader("Evidence")
    for line in packet.has_evidence_lines or []:
        direction = line.direction_of_evidence_provided or "?"
        score = line.score_of_evidence_provided
        st.markdown(f"**Line** — {direction} (score {score})")
        for item in line.has_evidence_items or []:
            render_item(store, packet_id, item)

    render_decisions(store, packet)


def render_item(store: PacketStore, packet_id: str, item: object) -> None:
    """Render a single evidence item and its per-item rating control."""
    kind = type(item).__name__
    item_id = getattr(item, "id", "")
    with st.container(border=True):
        st.markdown(f"`{kind}` — rating: **{getattr(item, 'rating', None) or 'unrated'}**")
        for attr in (
            "source_name", "source_id", "source_object", "title", "pmid", "doi",
            "quote", "method_name", "value", "trust_level", "contribution_type", "content",
        ):
            val = getattr(item, attr, None)
            if val:
                st.caption(f"{attr}: {val}")
        eco = getattr(item, "eco_code", None)
        if eco:
            st.caption(f"ECO: {eco} {getattr(item, 'eco_label', '') or ''}")

        curator_orcid, _ = get_curator_info()
        if curator_orcid and is_authorized_curator(curator_orcid):
            c1, c2 = st.columns(2)
            if c1.button("Accept item", key=f"acc_{packet_id}_{item_id}"):
                store.set_item_rating(packet_id, item_id, "ACCEPTED")
                st.rerun()
            if c2.button("Reject item", key=f"rej_{packet_id}_{item_id}"):
                store.set_item_rating(packet_id, item_id, "REJECTED")
                st.rerun()


def render_decisions(store: PacketStore, packet: EvidencePacket) -> None:
    """Show decision history and record a new decision."""
    packet_id = str(packet.id)
    st.subheader("Decision")

    history = store.get_decisions(packet_id)
    if history:
        for d in history:
            st.caption(f"{d['decided_at']} — {d['curator']}: **{d['decision']}** ({d['rationale'] or ''})")

    curator_orcid, curator_name = get_curator_info()
    if not (curator_orcid and is_authorized_curator(curator_orcid)):
        st.info("Log in as an authorised curator to record a decision.")
        return

    rationale = st.text_area("Rationale", key=f"rat_{packet_id}")
    decision_map = {"Accept": ("ACCEPT", "ACCEPTED"),
                    "Reject": ("REJECT", "REJECTED"),
                    "Controversial": ("CONTROVERSIAL", "CONTROVERSIAL")}
    cols = st.columns(len(decision_map))
    for col, (label, (decision, status)) in zip(cols, decision_map.items()):
        if col.button(label, key=f"dec_{label}_{packet_id}"):
            store.record_decision(
                CurationDecision(
                    id=f"dec_{uuid4().hex[:12]}",
                    packet_id=packet_id,
                    curator=curator_orcid,
                    curator_name=curator_name,
                    decision=DecisionType(decision),
                    rationale=rationale or None,
                    decided_at=datetime.now(),
                )
            )
            store.update_status(packet_id, status)
            st.success(f"Recorded {decision}.")
            st.rerun()


def render_ingest(store: PacketStore) -> None:
    """Ingest packets from a directory."""
    st.title("Ingest")
    from pathlib import Path

    from sieve.packet_ingest import ingest_packet_directory

    directory = st.text_input("Directory", "inbox/examples")
    if st.button("Ingest"):
        stats = ingest_packet_directory(Path(directory), store)
        st.success(f"Ingested {stats['success']} of {stats['files']} packets.")
        for err in stats["error_details"]:
            st.error(f"{err['file']}: {err['error']}")


def render_export(store: PacketStore) -> None:
    """Export ACCEPTED packets to RDF."""
    st.title("Export")
    from sieve.packet_export import export_packets_to_rdf

    rows = store.list_packets(status="ACCEPTED")
    st.write(f"{len(rows)} ACCEPTED packet(s) ready to export.")
    if st.button("Export accepted to RDF (Turtle)"):
        packets = [store.get_packet(r["id"]) for r in rows]
        rdf = export_packets_to_rdf([p for p in packets if p is not None])
        st.code(rdf, language="turtle")


if __name__ == "__main__":
    main()
