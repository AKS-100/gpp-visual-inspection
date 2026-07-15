"""Placeholder content for pages not yet built in the current phase."""

import streamlit as st


def coming_soon(page_name: str, phase_label: str) -> None:
    """
    Render a placeholder notice for a page whose real implementation
    lands in a later phase, so the nav shell can be reviewed end-to-end
    before every page has real data behind it.

    Args:
        page_name: e.g. "Factory overview".
        phase_label: e.g. "Phase 9 - Dashboard development".
    """
    st.markdown(
        f'<div class="gpp-card" style="text-align:center;padding:48px 24px">'
        f'<div style="color:var(--text-primary);font-family:var(--font-heading);font-size:16px">'
        f"{page_name}</div>"
        f'<div style="color:var(--text-secondary);font-size:13px;margin-top:8px">'
        f"Built in {phase_label}, once its data source is ready.</div>"
        f"</div>",
        unsafe_allow_html=True,
    )
