"""Batch lifecycle tracking — list, stage progress, stage history, and creation."""

import streamlit as st

from app.components import stage_progress, top_bar
from app.services import get_services
from config.settings import settings
from core.repositories.batch_repository import VALID_STAGES
from core.services.exceptions import InvalidStageTransitionError, ValidationError


@st.cache_data(ttl=15, show_spinner=False)
def _cached_batches_bundle():
    services = get_services()
    batches = services.batch_service.list_all_batches()
    components_by_id = {c.component_id: c.component_name for c in services.component_repository.get_all()}
    machines_by_id = {m.machine_id: m.machine_name for m in services.machine_repository.get_all(active_only=False)}
    return batches, components_by_id, machines_by_id


@st.cache_data(ttl=15, show_spinner=False)
def _cached_batch_details(batch_id: int):
    services = get_services()
    inspection_count = services.inspection_repository.count_by_batch(batch_id)
    history = services.batch_service.get_stage_history(batch_id)
    return inspection_count, history


def render() -> None:
    services = get_services()
    current_user = st.session_state[settings.session_keys.user]
    top_bar("Batches", current_user)

    with st.expander("Create new batch"):
        _render_create_batch_form(services)

    batches, components_by_id, machines_by_id = _cached_batches_bundle()
    if not batches:
        st.info("No batches created yet.")
        return

    batch_options = {f"{b.batch_code} — {components_by_id.get(b.component_id, '?')} ({b.status})": b for b in batches}
    selected_label = st.selectbox("Select a batch to view details", options=list(batch_options.keys()))
    selected = batch_options[selected_label]

    inspection_count, history = _cached_batch_details(selected.batch_id)
    open_entry = next((h for h in reversed(history) if h.exited_at is None), None)
    current_machine = machines_by_id.get(open_entry.machine_id, "Unassigned") if open_entry and open_entry.machine_id else "Unassigned"

    st.markdown(
        f'<div class="gpp-card" style="display:flex;justify-content:space-between;margin:12px 0">'
        f'<div><div class="gpp-kpi-label">Batch code</div><div class="gpp-kpi-value">{selected.batch_code}</div></div>'
        f'<div><div class="gpp-kpi-label">Completion</div><div class="gpp-kpi-value gpp-kpi-value--accent">{selected.completion_percent}%</div></div>'
        f'<div><div class="gpp-kpi-label">Quantity</div><div class="gpp-kpi-value">{selected.actual_quantity}/{selected.planned_quantity}</div></div>'
        f'<div><div class="gpp-kpi-label">Inspections</div><div class="gpp-kpi-value">{inspection_count}</div></div>'
        f'<div><div class="gpp-kpi-label">Current machine</div><div class="gpp-kpi-value">{current_machine}</div></div>'
        f'<div><div class="gpp-kpi-label">Status</div><div class="gpp-kpi-value">{selected.status}</div></div>'
        f"</div>",
        unsafe_allow_html=True,
    )

    st.markdown('<div class="gpp-section-label">Stage progress</div>', unsafe_allow_html=True)
    stage_progress(selected.current_stage)

    if selected.status == "In Progress":
        _render_advance_stage_control(services, selected)

    st.markdown('<div class="gpp-section-label">Stage history</div>', unsafe_allow_html=True)
    if history:
        em_dash = "—"
        rows = "".join(
            f"<tr><td>{h.stage}</td><td>{machines_by_id.get(h.machine_id, em_dash) if h.machine_id else em_dash}</td>"
            f"<td>{h.entered_at}</td><td>{h.exited_at or 'In progress'}</td>"
            f"<td>{'Simulated' if h.is_simulated else 'Real'}</td></tr>"
            for h in history
        )
        st.markdown(
            f'<table class="gpp-table"><thead><tr><th>Stage</th><th>Machine</th><th>Entered</th>'
            f'<th>Exited</th><th>Source</th></tr></thead><tbody>{rows}</tbody></table>',
            unsafe_allow_html=True,
        )
    else:
        st.info("No stage transitions recorded yet.")


def _render_create_batch_form(services) -> None:
    components = services.component_repository.get_all()
    if not components:
        st.warning("No component types configured. Add one from the Admin page first.")
        return

    with st.form("create_batch_form"):
        component_options = {c.component_name: c for c in components}
        component_name = st.selectbox("Component type", options=list(component_options.keys()))
        planned_quantity = st.number_input("Planned quantity", min_value=1, value=100, step=1)
        submitted = st.form_submit_button("Create batch", type="primary")

    if submitted:
        try:
            component = component_options[component_name]
            new_batch = services.batch_service.create_batch(component.component_id, int(planned_quantity))
            st.success(f"Batch {new_batch.batch_code} created.")
            st.cache_data.clear()
            st.rerun()
        except ValidationError as exc:
            st.error(str(exc))
        except Exception:
            import logging
            logging.getLogger(__name__).exception("Unexpected error creating batch")
            st.error("Couldn't create the batch due to an unexpected error.")


def _render_advance_stage_control(services, batch) -> None:
    current_index = VALID_STAGES.index(batch.current_stage)
    if current_index + 1 >= len(VALID_STAGES):
        return

    next_stage = VALID_STAGES[current_index + 1]
    if st.button(f"Advance to {next_stage}"):
        try:
            services.batch_service.advance_stage(batch.batch_id, next_stage, is_simulated=True)
            st.success(f"Batch advanced to {next_stage}.")
            st.cache_data.clear()
            st.rerun()
        except InvalidStageTransitionError as exc:
            st.error(str(exc))
