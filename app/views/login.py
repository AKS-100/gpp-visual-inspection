"""Login page. Rendered directly by app/main.py when no user is in session state."""

import streamlit as st

from config.settings import settings
from app.services import get_services
from app.assets import get_logo_img_tag
from core.services.auth_service import AuthService


def render() -> None:
    """Render the centered login card and handle credential submission."""
    # Top-right theme toggle bar so the user can switch theme before logging in
    _, top_right_col = st.columns([7.5, 1.2])
    with top_right_col:
        current_theme = st.session_state.get(settings.session_keys.theme_mode, "light")
        theme_label = "Dark Theme" if current_theme == "light" else "Light Theme"
        if st.button(theme_label, key="login_top_theme_btn", width="stretch"):
            st.session_state[settings.session_keys.theme_mode] = (
                "dark" if current_theme == "light" else "light"
            )
            st.rerun()

    _, center_col, _ = st.columns([1, 1.1, 1])

    with center_col:
        logo_tag = get_logo_img_tag(class_name="gpp-login-logo-ring")
        st.markdown(
            f'<div class="gpp-login-hero">'
            f'{logo_tag}'
            f'<div class="gpp-login-title">Visual Inspection Portal</div>'
            f'<div class="gpp-login-subtitle">'
            f'Smart Manufacturing Analytics · Ghaziabad Precision Products'
            f'</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

        with st.form("login_form"):
            st.markdown(
                '<div style="font-family:var(--font-heading);font-size:15px;'
                'font-weight:600;color:var(--text-primary);margin-bottom:14px">'
                "Sign in to your account</div>",
                unsafe_allow_html=True,
            )
            username = st.text_input("Username", placeholder="e.g. operator1")
            password = st.text_input("Password", type="password", placeholder="Enter your password")
            submitted = st.form_submit_button("Sign in", type="primary", width="stretch")

        st.markdown(
            '<div style="text-align:center;margin-top:12px;font-size:11.5px;color:var(--text-muted)">'
            "Ghaziabad Precision Products Pvt. Ltd. · Internal use only"
            "</div>",
            unsafe_allow_html=True,
        )

        if submitted:
            _handle_login(username, password)


def _handle_login(username: str, password: str) -> None:
    """Validate input and authenticate; on success, store the User in session state."""
    if not username or not password:
        st.error("Enter your username and password.")
        return

    auth_service = AuthService(get_services().user_repository)
    user = auth_service.authenticate(username, password)

    if user is None:
        st.error("That username or password isn't right. Try again.")
        return

    st.session_state[settings.session_keys.user] = user
    st.session_state.active_page = "factory_overview"
    st.rerun()
