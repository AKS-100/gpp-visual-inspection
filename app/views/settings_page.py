"""Application settings — every value backed by SettingsService, nothing hardcoded."""

import streamlit as st

from app.components import top_bar
from app.services import get_services
from config.settings import settings
from core.services.exceptions import ValidationError


def render() -> None:
    services = get_services()
    current_user = st.session_state[settings.session_keys.user]
    top_bar("Settings", current_user)

    if not current_user.is_admin:
        st.error("Your account doesn't have access to this page.")
        return

    settings_service = services.settings_service

    st.markdown('<div class="gpp-section-label">Appearance</div>', unsafe_allow_html=True)
    current_theme = st.session_state.get(settings.session_keys.theme_mode, "light")
    theme_choice = st.radio(
        "Application theme mode",
        options=["Light Theme", "Dark Industrial Theme"],
        index=0 if current_theme == "light" else 1,
        horizontal=True,
    )
    selected_mode = "light" if theme_choice == "Light Theme" else "dark"
    if selected_mode != current_theme:
        st.session_state[settings.session_keys.theme_mode] = selected_mode
        st.rerun()

    st.markdown('<div class="gpp-section-label">Inspection</div>', unsafe_allow_html=True)
    current_threshold = settings_service.get_confidence_threshold()
    new_threshold = st.slider(
        "Default confidence threshold",
        min_value=0.0, max_value=1.0, value=current_threshold, step=0.01,
        help="Inspections below this confidence may warrant manual review (display-only for now).",
    )

    st.markdown('<div class="gpp-section-label">Batch lifecycle</div>', unsafe_allow_html=True)
    current_qi_units = settings_service.get_qi_units_per_stage_advance()
    new_qi_units = st.number_input(
        "Inspections required before a batch auto-advances to Packing",
        min_value=1, value=current_qi_units, step=1,
    )

    if st.button("Save settings", type="primary"):
        try:
            settings_service.set_confidence_threshold(float(new_threshold), updated_by=current_user.user_id)
            settings_service.set_qi_units_per_stage_advance(int(new_qi_units), updated_by=current_user.user_id)
            st.success("Settings saved.")
            st.rerun()
        except ValidationError as exc:
            st.error(str(exc))

    st.markdown('<div class="gpp-section-label">All settings (raw)</div>', unsafe_allow_html=True)
    all_settings = settings_service.get_all()
    rows = "".join(f"<tr><td>{k}</td><td>{v}</td></tr>" for k, v in all_settings.items())
    st.markdown(
        f'<table class="gpp-table"><thead><tr><th>Key</th><th>Value</th></tr></thead><tbody>{rows}</tbody></table>',
        unsafe_allow_html=True,
    )
