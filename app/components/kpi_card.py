"""KPI card component."""

from typing import Literal, Optional

import streamlit as st

KpiEmphasis = Literal["default", "accent", "warning", "danger"]


def kpi_card(
    label: str,
    value: str,
    emphasis: KpiEmphasis = "default",
    delta: Optional[str] = None,
    delta_direction: Literal["up", "down"] = "up",
) -> None:
    """
    Render a single KPI metric card.

    Args:
        label: Muted caption above the value, e.g. "Acceptance rate".
        value: The pre-formatted display value, e.g. "96.4%". Formatting
            (rounding, unit symbols) is the caller's responsibility so this
            component stays presentation-only.
        emphasis: Which value color to use. "accent" for headline/premium
            metrics, "warning"/"danger" for metrics currently in a bad
            state, "default" otherwise.
        delta: Optional trend text, e.g. "+1.2% vs yesterday".
        delta_direction: Colors the delta green ("up") or red ("down").
    """
    value_class = {
        "default": "",
        "accent":  "gpp-kpi-value--accent",
        "warning": "gpp-kpi-value--warning",
        "danger":  "gpp-kpi-value--danger",
    }[emphasis]

    # Show a gold accent bar for headline metrics, teal for others
    accent_bar = (
        '<div class="gpp-kpi-accent-bar"></div>'
        if emphasis == "accent"
        else '<div class="gpp-kpi-accent-bar" style="background:var(--border)"></div>'
    )

    delta_html = ""
    if delta:
        delta_class = "gpp-kpi-delta--up" if delta_direction == "up" else "gpp-kpi-delta--down"
        arrow = "↑" if delta_direction == "up" else "↓"
        delta_html = f'<div class="gpp-kpi-delta {delta_class}">{arrow} {delta}</div>'

    st.markdown(
        f'<div class="gpp-card">'
        f'<div class="gpp-kpi-label">{label}</div>'
        f'<div class="gpp-kpi-value {value_class}">{value}</div>'
        f"{delta_html}"
        f"{accent_bar}"
        f"</div>",
        unsafe_allow_html=True,
    )
