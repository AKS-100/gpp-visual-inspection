"""
Application entry point.

Responsible for injecting the theme, gating access behind login, and
building the top-navigation shell.

Navigation uses a two-row layout:
  Row 1 — Brand bar (pure HTML): GPP logo + user info chip
  Row 2 — Tab strip (real st.button): one button per page + logout

Streamlit strips onclick attributes from st.markdown HTML, so all
interactive navigation must use actual st.button / st.form widgets.
"""

import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st

from app.views import admin, batches, dashboard, factory_overview, history, inspection, login
from app.views import settings_page
from app.theme import apply_theme
from app.assets import get_logo_img_tag
from config.settings import settings

# (page_key) → (display label, render function)
_PAGES: dict[str, tuple[str, object]] = {
    "factory_overview": ("Factory Overview", factory_overview.render),
    "inspection":       ("Inspection",       inspection.render),
    "dashboard":        ("Dashboard",        dashboard.render),
    "batches":          ("Batches",          batches.render),
    "history":          ("History",          history.render),
}

_ADMIN_PAGES: dict[str, tuple[str, object]] = {
    "admin":    ("Admin",    admin.render),
    "settings": ("Settings", settings_page.render),
}


def main() -> None:
    st.set_page_config(
        page_title=settings.app_name,
        layout="wide",
        initial_sidebar_state="collapsed",
    )
    apply_theme()

    if settings.session_keys.user not in st.session_state:
        login.render()
        return

    _render_authenticated_shell()


def _render_authenticated_shell() -> None:
    current_user = st.session_state[settings.session_keys.user]

    # Initialise active page
    if "active_page" not in st.session_state:
        st.session_state.active_page = "factory_overview"

    all_pages = dict(_PAGES)
    if current_user.is_admin:
        all_pages.update(_ADMIN_PAGES)

    if st.session_state.active_page not in all_pages:
        st.session_state.active_page = "factory_overview"

    _render_navbar(current_user, all_pages)

    # Render the active page
    _, render_fn = all_pages[st.session_state.active_page]
    try:
        render_fn()
    except Exception as exc:
        from streamlit.runtime.scriptrunner import RerunException, StopException
        if isinstance(exc, (RerunException, StopException)):
            raise
        logging.getLogger(__name__).exception("Unhandled error while rendering a page.")
        st.error(
            "Something went wrong loading this page. The issue has been logged. "
            "Try refreshing, or contact an administrator if this keeps happening."
        )


def _render_navbar(current_user, all_pages: dict) -> None:
    """
    Render the navigation shell: a teal brand bar (HTML) + a tab strip
    (real Streamlit buttons).

    Streamlit strips onclick/JS from st.markdown, so navigation is driven
    entirely by st.button widgets that set st.session_state.active_page
    and call st.rerun().
    """
    active = st.session_state.active_page
    initials = "".join(w[0].upper() for w in current_user.full_name.split()[:2]) or "U"

    # ── Row 1: decorative brand bar (pure HTML, no interactivity needed) ──
    logo_tag = get_logo_img_tag(class_name="gpp-navbar-logo")
    st.markdown(
        f'<div class="gpp-navbar">'
        f'  <div class="gpp-navbar-brand">'
        f'    {logo_tag}'
        f'    <div class="gpp-navbar-brand-text">'
        f'      <span class="gpp-navbar-brand-name">Visual Inspection Portal</span>'
        f'      <span class="gpp-navbar-brand-sub">Smart Manufacturing Analytics</span>'
        f'    </div>'
        f'  </div>'
        f'  <div class="gpp-navbar-user">'
        f'    <div class="gpp-navbar-user-info">'
        f'      <span class="gpp-navbar-user-name">{current_user.full_name}</span>'
        f'      <span class="gpp-navbar-user-role">{current_user.role}</span>'
        f'    </div>'
        f'    <div class="gpp-navbar-avatar">{initials}</div>'
        f'  </div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    page_items = list(all_pages.items())
    n = len(page_items)

    # Layout: [page tabs...] [flexible spacer] [theme toggle] [logout]
    cols = st.columns([1.6] * n + [0.5] + [1.0] + [1.1])

    for i, (page_key, (label, _)) in enumerate(page_items):
        with cols[i]:
            is_active = (page_key == active)
            if is_active:
                st.markdown(
                    f'<div class="gpp-navtab-active">{label}</div>',
                    unsafe_allow_html=True,
                )
            else:
                if st.button(label, key=f"nav_{page_key}", width="stretch"):
                    st.session_state.active_page = page_key
                    st.rerun()

    # Spacer column (empty except for hidden marker identifying this horizontal block to CSS!)
    with cols[n]:
        st.markdown('<span id="gpp-nav-marker" style="display:none"></span>', unsafe_allow_html=True)

    # Theme toggle button
    with cols[n + 1]:
        current_theme = st.session_state.get(settings.session_keys.theme_mode, "light")
        toggle_label = "Dark Theme" if current_theme == "light" else "Light Theme"
        if st.button(toggle_label, key="navbar_theme_toggle", width="stretch"):
            st.session_state[settings.session_keys.theme_mode] = "dark" if current_theme == "light" else "light"
            st.rerun()

    # Logout button
    with cols[n + 2]:
        if st.button("Log out", key="navbar_logout", width="stretch"):
            del st.session_state[settings.session_keys.user]
            st.session_state.pop("active_page", None)
            st.rerun()


if __name__ == "__main__":
    main()
