"""Factory Overview (digital twin) — powered by DashboardService and MachineService."""

import streamlit as st

from app.components import kpi_card, machine_tile, stage_progress, status_badge, top_bar
from app.services import get_services
from config.settings import settings


@st.cache_data(ttl=15, show_spinner=False)
def _cached_factory_overview_bundle():
    services = get_services()
    summary = services.dashboard_service.get_summary()
    batch_stats = services.dashboard_service.get_batch_statistics()
    active_model = services.ai_model_repository.get_active_model()
    machine_statuses = services.machine_service.get_all_statuses()
    active_summaries = [b for b in services.batch_service.list_all_batches() if b.status == "In Progress"]
    components_by_id = {c.component_id: c.component_name for c in services.component_repository.get_all()}
    inspection_counts = {b.batch_id: services.inspection_repository.count_by_batch(b.batch_id) for b in active_summaries[:5]}
    recent = services.dashboard_service.get_recent_inspections(limit=5)
    return summary, batch_stats, active_model, machine_statuses, active_summaries, components_by_id, inspection_counts, recent


def render() -> None:
    current_user = st.session_state[settings.session_keys.user]
    top_bar("Factory overview", current_user)

    (
        summary,
        batch_stats,
        active_model,
        machine_statuses,
        active_summaries,
        components_by_id,
        inspection_counts,
        recent,
    ) = _cached_factory_overview_bundle()

    active_batches = batch_stats.get("In Progress", 0)

    cols = st.columns(5)
    with cols[0]:
        kpi_card("Today's inspections", str(summary.today_production))
    with cols[1]:
        kpi_card("Active batches", str(active_batches), emphasis="accent")
    with cols[2]:
        kpi_card("Acceptance rate", f"{summary.acceptance_rate}%")
    with cols[3]:
        kpi_card("Rejection rate", f"{summary.defect_rate}%", emphasis="warning" if summary.defect_rate > 10 else "default")
    with cols[4]:
        st.markdown('<div class="gpp-kpi-label">AI model status</div>', unsafe_allow_html=True)
        if active_model:
            status_badge(f"{active_model.model_name} active", "running")
        else:
            status_badge("No active model", "error")

    st.markdown('<div class="gpp-section-label">Machine status</div>', unsafe_allow_html=True)

    if not machine_statuses:
        st.info("No machines configured yet.")
    else:
        machine_cols = st.columns(min(len(machine_statuses), 3))
        for index, machine in enumerate(machine_statuses):
            with machine_cols[index % len(machine_cols)]:
                status_label = "running" if machine.is_running else "idle"
                machine_tile(
                    machine.machine_name,
                    status_label,
                    detail=f"{machine.default_stage} · {machine.stage_history_count} batches processed",
                    is_processing=machine.is_running and machine.default_stage == "Heat Treatment",
                )

    st.markdown('<div class="gpp-section-label">Active batches — current stage &amp; progress</div>', unsafe_allow_html=True)

    if not active_summaries:
        st.info("No batches currently in progress. Create one from the Batches page.")
    else:
        for batch in active_summaries[:5]:
            inspection_count = inspection_counts.get(batch.batch_id, 0)
            st.markdown(
                f'<div style="display:flex;justify-content:space-between;color:var(--text-secondary);'
                f'font-size:12px;margin:8px 0 4px 2px">'
                f'<span>{batch.batch_code} · {components_by_id.get(batch.component_id, "?")} · '
                f'{batch.completion_percent}% complete</span>'
                f'<span>{inspection_count} inspection(s) recorded</span></div>',
                unsafe_allow_html=True,
            )
            stage_progress(batch.current_stage)

    st.markdown('<div class="gpp-section-label">Recent activity</div>', unsafe_allow_html=True)
    if not recent:
        st.info("No inspections recorded yet.")
    else:
        rows_html = "".join(
            f'<tr><td>#{r.inspection_id}</td><td>Batch {r.batch_id}</td>'
            f'<td>{r.prediction}</td><td>{r.confidence_score:.1%}</td><td>{r.inspected_at}</td></tr>'
            for r in recent
        )
        st.markdown(
            f'<table class="gpp-table"><thead><tr><th>ID</th><th>Batch</th><th>Result</th>'
            f'<th>Confidence</th><th>Time</th></tr></thead><tbody>{rows_html}</tbody></table>',
            unsafe_allow_html=True,
        )
