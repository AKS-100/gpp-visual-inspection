"""Persistent page sub-header — page title, shift, AI status, live clock."""

from datetime import datetime

import streamlit as st

from core.services.auth_service import User


def top_bar(page_title: str, current_user: User, ai_system_online: bool = True) -> None:
    """
    Render a lightweight page sub-header below the navbar.

    Shows the page name, current shift, AI system status, and a live clock.
    The global navbar handles branding and routing; this component focuses
    purely on per-page context.

    Args:
        page_title: Name of the current page, e.g. "Factory Overview".
        current_user: The logged-in user, used to display their shift.
        ai_system_online: Reflects whether the ML inference service is
            reachable. Defaults True until a real health-check is wired up.
    """
    status_label = "System Active" if ai_system_online else "System Offline"
    status_class = "gpp-status-running" if ai_system_online else "gpp-status-error"
    now = datetime.now().strftime("%H:%M:%S")

    st.markdown(
        f'<div class="gpp-topbar">'
        f'<div style="display:flex;align-items:center;gap:4px">'
        f'<span class="gpp-topbar-title">{page_title}</span>'
        f'<span class="gpp-topbar-meta">· {current_user.shift_name}</span>'
        f"</div>"
        f'<div style="display:flex;align-items:center;gap:12px">'
        f'<span class="gpp-status-badge {status_class}">'
        f'<span class="gpp-dot"></span>{status_label}</span>'
        f'<span class="gpp-topbar-clock">{now}</span>'
        f"</div>"
        f"</div>",
        unsafe_allow_html=True,
    )
