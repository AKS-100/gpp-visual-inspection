"""Manufacturing KPI dashboard — Plotly charts, all data from DashboardService."""

import plotly.graph_objects as go
import streamlit as st

from app.components import kpi_card, top_bar
from app.services import get_services
from config.settings import settings

PLOTLY_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Inter, sans-serif", color="#5A4F3E", size=12),
    margin=dict(l=10, r=10, t=30, b=10),
    legend=dict(orientation="h", yanchor="bottom", y=1.02),
)


@st.cache_data(ttl=15, show_spinner=False)
def _cached_dashboard_summary():
    return get_services().dashboard_service.get_summary()


@st.cache_data(ttl=15, show_spinner=False)
def _cached_batch_stats():
    return get_services().dashboard_service.get_batch_statistics()


@st.cache_data(ttl=15, show_spinner=False)
def _cached_recent_inspections(limit: int):
    return get_services().dashboard_service.get_recent_inspections(limit=limit)


@st.cache_data(ttl=15, show_spinner=False)
def _cached_build_trend_chart(days: int):
    trend = get_services().dashboard_service.get_trend(days=days)
    if not any(p.good_count or p.defective_count for p in trend):
        return None

    dates = [p.date for p in trend]
    good = [p.good_count for p in trend]
    defective = [p.defective_count for p in trend]
    acceptance = [
        round(g / (g + d) * 100, 1) if (g + d) else 0 for g, d in zip(good, defective)
    ]

    fig = go.Figure()
    fig.add_bar(x=dates, y=good, name="Good", marker_color="#5CAE73")
    fig.add_bar(x=dates, y=defective, name="Defective", marker_color="#D9483B")
    fig.add_trace(go.Scatter(
        x=dates, y=acceptance, name="Acceptance %", yaxis="y2",
        line=dict(color="#C9A24B", width=2), mode="lines+markers",
    ))
    fig.update_layout(
        **PLOTLY_LAYOUT,
        barmode="stack",
        yaxis=dict(title="Inspections", gridcolor="#D9D1C5"),
        yaxis2=dict(title="Acceptance %", overlaying="y", side="right", range=[0, 100]),
        xaxis=dict(gridcolor="#D9D1C5"),
        height=320,
    )
    return fig


@st.cache_data(ttl=15, show_spinner=False)
def _cached_build_defect_chart():
    breakdown = get_services().dashboard_service.get_defect_breakdown()
    if not breakdown:
        return None

    fig = go.Figure(go.Bar(
        x=list(breakdown.values()), y=list(breakdown.keys()), orientation="h", marker_color="#C9A24B",
    ))
    fig.update_layout(**PLOTLY_LAYOUT, xaxis=dict(gridcolor="#D9D1C5"), yaxis=dict(autorange="reversed"), height=320)
    return fig


@st.cache_data(ttl=15, show_spinner=False)
def _cached_build_utilization_chart():
    utilization = get_services().dashboard_service.get_machine_utilization()
    if not utilization:
        return None

    fig = go.Figure(go.Bar(
        x=list(utilization.keys()), y=list(utilization.values()), marker_color="#A66B3B",
    ))
    fig.update_layout(**PLOTLY_LAYOUT, xaxis=dict(gridcolor="#D9D1C5"), yaxis=dict(gridcolor="#D9D1C5", title="Batches processed"), height=280)
    return fig


@st.cache_data(ttl=15, show_spinner=False)
def _cached_build_confidence_chart():
    recent = get_services().dashboard_service.get_recent_inspections(limit=200)
    if not recent:
        return None

    confidences = [r.confidence_score * 100 for r in recent]
    fig = go.Figure(go.Histogram(x=confidences, nbinsx=20, marker_color="#4FB6C4"))
    fig.update_layout(**PLOTLY_LAYOUT, xaxis=dict(title="Confidence %", gridcolor="#D9D1C5"), yaxis=dict(title="Count", gridcolor="#D9D1C5"), height=280)
    return fig


def render() -> None:
    services = get_services()
    current_user = st.session_state[settings.session_keys.user]
    top_bar("Dashboard", current_user)

    summary = _cached_dashboard_summary()

    cols = st.columns(4)
    with cols[0]:
        kpi_card("Total inspections", str(summary.total_inspections))
    with cols[1]:
        kpi_card("Acceptance rate", f"{summary.acceptance_rate}%", emphasis="accent")
    with cols[2]:
        kpi_card("Defect rate", f"{summary.defect_rate}%", emphasis="warning" if summary.defect_rate > 10 else "default")
    with cols[3]:
        kpi_card("Today's production", str(summary.today_production))

    if summary.total_inspections == 0:
        st.info("No inspections recorded yet. Run an inspection from the Inspection page to populate this dashboard.")
        return

    trend_days = st.select_slider("Trend window", options=[7, 14, 30], value=7)

    col_trend, col_defects = st.columns(2)
    with col_trend:
        st.markdown('<div class="gpp-section-label">Production &amp; acceptance trend</div>', unsafe_allow_html=True)
        _render_trend_chart(services, trend_days)

    with col_defects:
        st.markdown('<div class="gpp-section-label">Defect distribution</div>', unsafe_allow_html=True)
        _render_defect_chart(services)

    col_util, col_conf = st.columns(2)
    with col_util:
        st.markdown('<div class="gpp-section-label">Machine utilization (proxy metric)</div>', unsafe_allow_html=True)
        _render_utilization_chart(services)
        st.caption("Proxy metric based on stage-history activity — see docs/FutureScope.md for real telemetry plans.")

    with col_conf:
        st.markdown('<div class="gpp-section-label">Confidence distribution</div>', unsafe_allow_html=True)
        _render_confidence_chart(services)

    st.markdown('<div class="gpp-section-label">Batch statistics</div>', unsafe_allow_html=True)
    batch_stats = _cached_batch_stats()
    if batch_stats:
        stat_cols = st.columns(len(batch_stats))
        for col, (status, count) in zip(stat_cols, batch_stats.items()):
            with col:
                kpi_card(status, str(count))
    else:
        st.info("No batches created yet.")

    st.markdown('<div class="gpp-section-label">Recent inspections</div>', unsafe_allow_html=True)
    recent = _cached_recent_inspections(limit=10)
    rows = "".join(
        f"<tr><td>#{r.inspection_id}</td><td>{r.prediction}</td><td>{r.confidence_score:.1%}</td><td>{r.inspected_at}</td></tr>"
        for r in recent
    )
    st.markdown(
        f'<table class="gpp-table"><thead><tr><th>ID</th><th>Result</th><th>Confidence</th><th>Time</th></tr></thead>'
        f'<tbody>{rows}</tbody></table>',
        unsafe_allow_html=True,
    )

    st.markdown('<div class="gpp-section-label">Export report</div>', unsafe_allow_html=True)
    col_csv, col_pdf = st.columns(2)
    with col_csv:
        if st.button("Export CSV", width="stretch"):
            with st.spinner("Generating CSV report..."):
                try:
                    path = services.report_service.export_csv(current_user.user_id)
                    with open(path, "rb") as f:
                        st.download_button("Download CSV", f, file_name=path.name, mime="text/csv", width="stretch")
                    st.success(f"Report saved to {path}")
                except Exception:
                    import logging
                    logging.getLogger(__name__).exception("CSV export failed")
                    st.error("Couldn't generate the CSV report.")
    with col_pdf:
        if st.button("Export PDF", width="stretch"):
            with st.spinner("Generating PDF report..."):
                try:
                    path = services.report_service.export_pdf(current_user.user_id)
                    with open(path, "rb") as f:
                        st.download_button("Download PDF", f, file_name=path.name, mime="application/pdf", width="stretch")
                    st.success(f"Report saved to {path}")
                except Exception:
                    import logging
                    logging.getLogger(__name__).exception("PDF export failed")
                    st.error("Couldn't generate the PDF report.")


def _render_trend_chart(services, days: int) -> None:
    fig = _cached_build_trend_chart(days)
    if not fig:
        st.info(f"No inspections in the last {days} days.")
        return
    st.plotly_chart(fig, width="stretch")


def _render_defect_chart(services) -> None:
    fig = _cached_build_defect_chart()
    if not fig:
        st.info("No defects recorded yet.")
        return
    st.plotly_chart(fig, width="stretch")


def _render_utilization_chart(services) -> None:
    fig = _cached_build_utilization_chart()
    if not fig:
        st.info("No machine activity recorded yet.")
        return
    st.plotly_chart(fig, width="stretch")


def _render_confidence_chart(services) -> None:
    fig = _cached_build_confidence_chart()
    if not fig:
        st.info("No inspections recorded yet.")
        return
    st.plotly_chart(fig, width="stretch")
