"""Status badge component."""

from typing import Literal

import streamlit as st

StatusKind = Literal["running", "idle", "error", "info"]


def status_badge(label: str, status: StatusKind) -> None:
    """
    Render a colored-dot status pill.

    Args:
        label: Text shown next to the dot, e.g. "Running", "Defective".
        status: One of "running" (green), "idle" (amber), "error" (red),
            "info" (cyan). Maps directly to the semantic status tokens in
            theme.css — never pass a color, only a meaning.
    """
    st.markdown(
        f'<span class="gpp-status-badge gpp-status-{status}">'
        f'<span class="gpp-dot"></span>{label}</span>',
        unsafe_allow_html=True,
    )
