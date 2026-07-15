"""Machine status tile component."""

from typing import Literal

import streamlit as st

MachineStatus = Literal["running", "idle", "error"]

_STATUS_LABEL = {"running": "Running", "idle": "Idle", "error": "Maintenance"}


def machine_tile(
    machine_name: str,
    status: MachineStatus,
    detail: str,
    is_processing: bool = False,
) -> None:
    """
    Render a single machine's status card.

    Args:
        machine_name: e.g. "Forge press 01".
        status: Drives the status badge color.
        detail: Secondary line, typically the current batch code or a
            short state description.
        is_processing: When True, renders the furnace-glow card variant
            reserved for actively-heating / actively-processing states
            (e.g. a machine currently in the Heat Treatment stage). Use
            sparingly — this is the app's one attention-drawing motif.
    """
    card_class = "gpp-card-glow" if is_processing else "gpp-card"
    status_icon = (
        '<i class="ti ti-flame" style="font-size:12px;color:var(--accent-glow)" aria-hidden="true"></i> processing'
        if is_processing
        else f'<span class="gpp-status-badge gpp-status-{status}"><span class="gpp-dot"></span>{_STATUS_LABEL[status]}</span>'
    )

    st.markdown(
        f'<div class="{card_class}">'
        f'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">'
        f'<span style="color:var(--text-primary);font-size:13px;font-weight:500">{machine_name}</span>'
        f'<span style="font-size:11px;color:var(--text-secondary)">{status_icon}</span>'
        f"</div>"
        f'<div style="color:var(--text-secondary);font-size:11px">{detail}</div>'
        f"</div>",
        unsafe_allow_html=True,
    )
