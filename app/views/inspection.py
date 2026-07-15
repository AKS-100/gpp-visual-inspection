"""Inspection workflow — batch, machine, component selection through to AI prediction and save."""

import logging
from pathlib import Path

import streamlit as st

from app.components import status_badge, top_bar
from app.services import get_services
from config.settings import settings
from core.services.exceptions import NotFoundError, ServiceError

logger = logging.getLogger(__name__)

# Session state key for storing the last inspection outcome
_RESULT_KEY = "insp_last_outcome"


def render() -> None:
    services = get_services()
    current_user = st.session_state[settings.session_keys.user]
    top_bar("Inspection", current_user)

    batches_at_qi = services.batch_service.list_batches_at_stage("Quality Inspection")

    if not batches_at_qi:
        st.info(
            "No batches are currently at the Quality Inspection stage. "
            "Advance a batch through Forging → Machining → Heat Treatment from the Batches page first."
        )
        return

    st.markdown('<div class="gpp-section-label">1. Select batch</div>', unsafe_allow_html=True)
    batch_options = {f"{b.batch_code} ({b.completion_percent}% complete)": b for b in batches_at_qi}
    selected_batch_label = st.selectbox("Batch", options=list(batch_options.keys()), label_visibility="collapsed")
    selected_batch = batch_options[selected_batch_label]

    component = services.component_repository.get_by_id(selected_batch.component_id)

    col_machine, col_component = st.columns(2)
    with col_machine:
        st.markdown('<div class="gpp-section-label">2. Select machine</div>', unsafe_allow_html=True)
        qi_machines = services.machine_service.get_machines_for_stage("Quality Inspection")
        if qi_machines:
            machine_options = {m.machine_name: m for m in qi_machines}
            selected_machine_name = st.selectbox("Machine", options=list(machine_options.keys()), label_visibility="collapsed")
            selected_machine = machine_options[selected_machine_name]
        else:
            st.warning("No inspection stations configured.")
            selected_machine = None

    with col_component:
        st.markdown('<div class="gpp-section-label">3. Component</div>', unsafe_allow_html=True)
        st.markdown(
            f'<div class="gpp-card">{component.component_name if component else "Unknown"}</div>',
            unsafe_allow_html=True,
        )

    st.markdown('<div class="gpp-section-label">4. Upload component image</div>', unsafe_allow_html=True)
    uploaded_file = st.file_uploader("Image", type=["jpg", "jpeg", "png"], label_visibility="collapsed")

    if uploaded_file is not None:
        col_preview, col_result = st.columns([1, 1.3])

        with col_preview:
            st.markdown('<div class="gpp-section-label">Preview</div>', unsafe_allow_html=True)
            # Fixed width so the image doesn't fill the entire column
            st.image(uploaded_file, width=260)

            if component is None:
                st.error("The component type for this batch no longer exists. Contact an administrator.")
            else:
                st.markdown('<div style="margin-top:10px"></div>', unsafe_allow_html=True)
                run_clicked = st.button("Run AI Inspection", type="primary")

        # ── Result column — only populated after a successful run ──────
        with col_result:
            # Show result from a previous run in this session (survives reruns
            # caused by other widgets changing, but not button clicks).
            outcome = st.session_state.get(_RESULT_KEY)
            if outcome:
                _display_result(services, outcome)

        if run_clicked:
            # Clear any previous result before starting a new inspection
            st.session_state.pop(_RESULT_KEY, None)
            outcome = _run_inspection(
                services, selected_batch, component,
                selected_machine, current_user, uploaded_file,
            )
            if outcome is not None:
                st.session_state[_RESULT_KEY] = outcome
                st.rerun()   # re-render so col_result shows the fresh result

    st.markdown('<div class="gpp-section-label">Inspection history for this batch</div>', unsafe_allow_html=True)
    _render_batch_history(services, selected_batch.batch_id)


def _run_inspection(services, batch, component, machine, current_user, uploaded_file):
    """Run the AI inspection and return the outcome, or None on failure."""
    upload_dir = settings.paths.uploaded_images_dir
    upload_dir.mkdir(parents=True, exist_ok=True)
    image_path = upload_dir / f"{batch.batch_code}_{uploaded_file.name}"
    image_path.write_bytes(uploaded_file.getvalue())

    try:
        with st.spinner("Running AI inspection…"):
            outcome = services.inspection_service.run_inspection(
                batch_id=batch.batch_id,
                component_id=component.component_id,
                operator_id=current_user.user_id,
                image_path=str(image_path),
                machine_id=machine.machine_id if machine else None,
            )
    except (ServiceError, NotFoundError) as exc:
        st.error(str(exc))
        logger.warning("Inspection rejected: %s", exc)
        return None
    except Exception:
        logger.exception("Unexpected error running inspection for batch %s", batch.batch_id)
        st.error("The inspection couldn't be completed due to an unexpected error. Please try again.")
        return None

    st.success(f"Inspection #{outcome.inspection_id} saved.")
    if outcome.batch_advanced:
        st.info(f"Batch {batch.batch_code} reached its inspection threshold and advanced to Packing.")

    st.cache_data.clear()
    return outcome


def _display_result(services, outcome) -> None:
    """Render prediction + confidence + Grad-CAM in the result column side by side."""
    st.markdown('<div class="gpp-section-label">Result</div>', unsafe_allow_html=True)

    col_hm, col_stats = st.columns([1.1, 1])

    with col_hm:
        st.markdown('<div style="font-size:11px;font-weight:600;color:var(--text-muted);text-transform:uppercase;margin-bottom:8px">Grad-CAM Heatmap</div>', unsafe_allow_html=True)
        if outcome.heatmap_path and Path(outcome.heatmap_path).exists():
            st.image(outcome.heatmap_path, width=260)
        else:
            st.caption("Heatmap not available.")

    with col_stats:
        st.markdown('<div style="font-size:11px;font-weight:600;color:var(--text-muted);text-transform:uppercase;margin-bottom:8px">Prediction</div>', unsafe_allow_html=True)
        badge_status = "running" if outcome.prediction == "GOOD" else "error"
        status_badge(outcome.prediction, badge_status)

        st.markdown(
            f'<div class="gpp-card" style="margin-top:12px">'
            f'<div class="gpp-kpi-label">Confidence</div>'
            f'<div class="gpp-kpi-value">{outcome.confidence_score:.1%}</div>'
            f"</div>",
            unsafe_allow_html=True,
        )

        if outcome.defect_ids:
            defect_names = {d.defect_id: d.defect_name for d in services.defect_repository.get_all()}
            detected = ", ".join(defect_names.get(d, f"defect {d}") for d in outcome.defect_ids)
            st.warning(f"Detected defects: {detected}")


def _render_batch_history(services, batch_id: int) -> None:
    records = services.inspection_repository.list_by_batch(batch_id)
    if not records:
        st.info("No inspections recorded for this batch yet.")
        return

    rows = "".join(
        f"<tr><td>#{r.inspection_id}</td><td>{r.prediction}</td>"
        f"<td>{r.confidence_score:.1%}</td><td>{r.inspected_at}</td></tr>"
        for r in records[:10]
    )
    st.markdown(
        f'<table class="gpp-table"><thead><tr>'
        f'<th>ID</th><th>Result</th><th>Confidence</th><th>Time</th>'
        f'</tr></thead><tbody>{rows}</tbody></table>',
        unsafe_allow_html=True,
    )
