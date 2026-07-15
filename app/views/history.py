"""Inspection history — search, filter, and browse past inspections, with image/heatmap preview."""

from pathlib import Path

import streamlit as st

from app.components import top_bar
from app.services import get_services
from config.settings import settings

PAGE_SIZE = 25


@st.cache_data(ttl=15, show_spinner=False)
def _cached_history_metadata():
    services = get_services()
    machines = services.machine_repository.get_all(active_only=False)
    components = services.component_repository.get_all()
    return machines, components


@st.cache_data(ttl=15, show_spinner=False)
def _cached_history_search(prediction, batch_code, date_from, date_to, confidence_min, confidence_max, machine_id, component_id, limit):
    services = get_services()
    return services.inspection_repository.search(
        prediction=prediction,
        batch_code=batch_code,
        date_from=date_from,
        date_to=date_to,
        confidence_min=confidence_min,
        confidence_max=confidence_max,
        machine_id=machine_id,
        component_id=component_id,
        limit=limit,
    )


def render() -> None:
    services = get_services()
    current_user = st.session_state[settings.session_keys.user]
    top_bar("History", current_user)

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        batch_code_filter = st.text_input("Batch code contains", placeholder="GPP-2026-0001")
    with col2:
        prediction_filter = st.selectbox("Result", options=["All", "GOOD", "DEFECTIVE"])
    with col3:
        date_from = st.date_input("From", value=None)
    with col4:
        date_to = st.date_input("To", value=None)

    col5, col6, col7 = st.columns(3)
    machines, components = _cached_history_metadata()
    with col5:
        machine_options = {"All": None} | {m.machine_name: m.machine_id for m in machines}
        machine_choice = st.selectbox("Machine", options=list(machine_options.keys()))
    with col6:
        component_options = {"All": None} | {c.component_name: c.component_id for c in components}
        component_choice = st.selectbox("Component", options=list(component_options.keys()))
    with col7:
        confidence_range = st.slider("Confidence range", 0.0, 1.0, (0.0, 1.0), step=0.05)

    results = _cached_history_search(
        prediction=None if prediction_filter == "All" else prediction_filter,
        batch_code=batch_code_filter or None,
        date_from=date_from.isoformat() if date_from else None,
        date_to=date_to.isoformat() if date_to else None,
        confidence_min=confidence_range[0],
        confidence_max=confidence_range[1],
        machine_id=machine_options[machine_choice],
        component_id=component_options[component_choice],
        limit=500,
    )

    st.markdown(f'<div class="gpp-section-label">{len(results)} result(s)</div>', unsafe_allow_html=True)

    if not results:
        st.info("No inspections match these filters. Try widening the date range or confidence range.")
        return

    if "history_page" not in st.session_state:
        st.session_state["history_page"] = 0

    total_pages = max(1, (len(results) - 1) // PAGE_SIZE + 1)
    st.session_state["history_page"] = min(st.session_state["history_page"], total_pages - 1)
    page = st.session_state["history_page"]

    page_results = results[page * PAGE_SIZE : (page + 1) * PAGE_SIZE]
    rows = "".join(
        f"<tr><td>#{r.inspection_id}</td><td>{r.batch_code}</td><td>{r.component_name}</td>"
        f"<td>{r.machine_name}</td><td>{r.operator_name}</td><td>{r.prediction}</td>"
        f"<td>{r.confidence_score:.1%}</td><td>{r.inspected_at}</td></tr>"
        for r in page_results
    )
    st.markdown(
        f'<table class="gpp-table"><thead><tr><th>ID</th><th>Batch</th><th>Component</th>'
        f'<th>Machine</th><th>Operator</th><th>Result</th><th>Confidence</th><th>Time</th></tr></thead>'
        f'<tbody>{rows}</tbody></table>',
        unsafe_allow_html=True,
    )

    if total_pages > 1:
        col_prev, col_label, col_next = st.columns([1, 2, 1])
        with col_prev:
            if st.button("← Previous", disabled=page == 0):
                st.session_state["history_page"] -= 1
                st.rerun()
        with col_label:
            st.markdown(
                f'<div style="text-align:center;color:var(--text-secondary);padding-top:8px">'
                f'Page {page + 1} of {total_pages}</div>',
                unsafe_allow_html=True,
            )
        with col_next:
            if st.button("Next →", disabled=page >= total_pages - 1):
                st.session_state["history_page"] += 1
                st.rerun()

    st.markdown('<div class="gpp-section-label">Inspect a record</div>', unsafe_allow_html=True)
    record_options = {f"#{r.inspection_id} — {r.batch_code} — {r.prediction}": r for r in page_results}
    selected_label = st.selectbox("Select a record to preview its image", options=["None"] + list(record_options.keys()))

    if selected_label != "None":
        record = record_options[selected_label]
        col_img, col_heatmap = st.columns(2)
        with col_img:
            st.markdown('<div class="gpp-kpi-label">Original image</div>', unsafe_allow_html=True)
            if Path(record.image_path).exists():
                st.image(record.image_path, width=280)
            else:
                st.caption("Image file no longer available on disk.")
        with col_heatmap:
            st.markdown('<div class="gpp-kpi-label">Grad-CAM heatmap</div>', unsafe_allow_html=True)
            if record.heatmap_path and Path(record.heatmap_path).exists():
                st.image(record.heatmap_path, width=280)
            else:
                st.caption("No heatmap available for this inspection.")
