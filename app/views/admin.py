"""Admin page — full CRUD for machines, components, AI models, and users."""

import streamlit as st

from app.components import top_bar
from app.services import get_services
from config.settings import settings
from core.services.auth_service import AuthService

MACHINE_TYPES = ["Forge Press", "CNC Lathe", "Heat Treatment Furnace", "Inspection Station", "Packing Station"]
STAGE_BY_TYPE = {
    "Forge Press": "Forging", "CNC Lathe": "Machining", "Heat Treatment Furnace": "Heat Treatment",
    "Inspection Station": "Quality Inspection", "Packing Station": "Packing",
}


def render() -> None:
    current_user = st.session_state[settings.session_keys.user]
    top_bar("Admin", current_user)

    if not current_user.is_admin:
        st.error("Your account doesn't have access to this page.")
        return

    services = get_services()
    tab_machines, tab_components, tab_models, tab_users = st.tabs(
        ["Machines", "Component types", "AI models", "Users"]
    )

    with tab_machines:
        _render_machines_tab(services)
    with tab_components:
        _render_components_tab(services)
    with tab_models:
        _render_models_tab(services)
    with tab_users:
        _render_users_tab(services)


# ---------------------------------------------------------------- Machines

def _render_machines_tab(services) -> None:
    with st.expander("Add machine"):
        with st.form("add_machine_form", clear_on_submit=True):
            name = st.text_input("Machine name")
            machine_type = st.selectbox("Machine type", options=MACHINE_TYPES)
            submitted = st.form_submit_button("Add machine", type="primary")
        if submitted:
            if not name.strip():
                st.error("Machine name is required.")
            else:
                services.machine_repository.create(name.strip(), machine_type, STAGE_BY_TYPE[machine_type])
                st.success(f"Machine '{name}' added.")
                st.rerun()

    st.markdown('<div class="gpp-section-label">Existing machines</div>', unsafe_allow_html=True)
    machines = services.machine_repository.get_all(active_only=False)
    if not machines:
        st.info("No machines configured yet.")
        return

    for m in machines:
        col_name, col_type, col_stage, col_status, col_edit, col_toggle = st.columns([2, 2, 2, 1, 1, 1])
        col_name.write(m.machine_name)
        col_type.write(m.machine_type)
        col_stage.write(m.default_stage)
        col_status.write("Active" if m.is_active else "Inactive")
        if col_edit.button("Edit", key=f"edit_machine_{m.machine_id}"):
            _edit_machine_dialog(services, m)
        if col_toggle.button("Deactivate" if m.is_active else "Activate", key=f"toggle_machine_{m.machine_id}"):
            services.machine_repository.set_active(m.machine_id, not m.is_active)
            st.rerun()


@st.dialog("Edit machine")
def _edit_machine_dialog(services, machine) -> None:
    name = st.text_input("Machine name", value=machine.machine_name)
    type_index = MACHINE_TYPES.index(machine.machine_type) if machine.machine_type in MACHINE_TYPES else 0
    machine_type = st.selectbox("Machine type", options=MACHINE_TYPES, index=type_index)
    if st.button("Save changes", type="primary"):
        if not name.strip():
            st.error("Machine name is required.")
        else:
            services.machine_repository.update(machine.machine_id, name.strip(), machine_type, STAGE_BY_TYPE[machine_type])
            st.rerun()


# ---------------------------------------------------------------- Components

def _render_components_tab(services) -> None:
    with st.expander("Add component type"):
        with st.form("add_component_form", clear_on_submit=True):
            name = st.text_input("Component name")
            description = st.text_input("Description")
            cycle_time = st.number_input("Target cycle time (seconds)", min_value=1, value=45, step=1)
            submitted = st.form_submit_button("Add component type", type="primary")
        if submitted:
            if not name.strip():
                st.error("Component name is required.")
            else:
                services.component_repository.create(name.strip(), description, int(cycle_time))
                st.success(f"Component type '{name}' added.")
                st.rerun()

    st.markdown('<div class="gpp-section-label">Existing component types</div>', unsafe_allow_html=True)
    components = services.component_repository.get_all(active_only=False)
    if not components:
        st.info("No component types configured yet.")
        return

    for c in components:
        col_name, col_desc, col_cycle, col_status, col_edit, col_toggle = st.columns([2, 3, 1, 1, 1, 1])
        col_name.write(c.component_name)
        col_desc.write(c.description or "")
        value = f"{c.target_cycle_time_sec}s" if c.target_cycle_time_sec is not None else "—"
        col_cycle.write(value)
        col_status.write("Active" if c.is_active else "Inactive")
        if col_edit.button("Edit", key=f"edit_component_{c.component_id}"):
            _edit_component_dialog(services, c)
        if col_toggle.button("Deactivate" if c.is_active else "Activate", key=f"toggle_component_{c.component_id}"):
            services.component_repository.set_active(c.component_id, not c.is_active)
            st.rerun()


@st.dialog("Edit component type")
def _edit_component_dialog(services, component) -> None:
    name = st.text_input("Component name", value=component.component_name)
    description = st.text_input("Description", value=component.description or "")
    cycle_time = st.number_input("Target cycle time (seconds)", min_value=1, value=component.target_cycle_time_sec or 45, step=1)
    if st.button("Save changes", type="primary"):
        if not name.strip():
            st.error("Component name is required.")
        else:
            services.component_repository.update(component.component_id, name.strip(), description, int(cycle_time))
            st.rerun()


# ---------------------------------------------------------------- AI models

def _render_models_tab(services) -> None:
    with st.expander("Register new model"):
        with st.form("add_model_form", clear_on_submit=True):
            model_name = st.text_input("Model name", placeholder="mobilenetv2-defect-classifier")
            version = st.text_input("Version", placeholder="1.0.0")
            framework = st.selectbox("Framework", options=["tensorflow", "pytorch", "onnx"])
            file_path = st.text_input("Model file path", placeholder="models/my_model.keras")
            notes = st.text_area("Notes", placeholder="Training dataset, accuracy, etc.")
            submitted = st.form_submit_button("Register model", type="primary")
        if submitted:
            if not model_name.strip() or not version.strip() or not file_path.strip():
                st.error("Model name, version, and file path are required.")
            else:
                services.ai_model_repository.create(model_name.strip(), version.strip(), framework, file_path.strip(), notes)
                st.success(f"Model '{model_name}' registered (inactive). Activate it below to use it.")
                st.rerun()

    st.markdown('<div class="gpp-section-label">Registered AI models</div>', unsafe_allow_html=True)
    models = services.ai_model_repository.get_all()
    if not models:
        st.info("No models registered.")
        return

    for m in models:
        col1, col2, col3 = st.columns([2, 2, 1])
        col1.markdown(f"**{m.model_name}** `{m.version}`")
        col2.caption(m.file_path)
        with col3:
            if m.is_active:
                st.markdown(
                    '<span class="gpp-status-badge gpp-status-running"><span class="gpp-dot"></span>Active</span>',
                    unsafe_allow_html=True,
                )
                if st.button("Deactivate", key=f"deactivate_model_{m.model_id}"):
                    services.ai_model_repository.deactivate_model(m.model_id)
                    st.rerun()
            else:
                if st.button("Activate", key=f"activate_model_{m.model_id}"):
                    services.ai_model_repository.activate_model(m.model_id)
                    st.rerun()


# ---------------------------------------------------------------- Users

def _render_users_tab(services) -> None:
    shifts = services.shift_repository.get_all()
    with st.expander("Add user"):
        with st.form("add_user_form", clear_on_submit=True):
            username = st.text_input("Username")
            full_name = st.text_input("Full name")
            password = st.text_input("Temporary password", type="password")
            role = st.selectbox("Role", options=["operator", "admin"])
            shift_name = st.selectbox("Shift", options=[s.shift_name for s in shifts])
            submitted = st.form_submit_button("Add user", type="primary")
        if submitted:
            if not username.strip() or not password or not full_name.strip():
                st.error("Username, full name, and password are all required.")
            else:
                role_id = services.user_repository.get_role_id(role)
                shift_id = next(s.shift_id for s in shifts if s.shift_name == shift_name)
                salt = username.strip()
                password_hash = AuthService.hash_password(password, salt)
                services.user_repository.create_user(username.strip(), password_hash, salt, full_name.strip(), role_id, shift_id)
                st.success(f"User '{username}' created.")
                st.rerun()

    st.markdown('<div class="gpp-section-label">Existing users</div>', unsafe_allow_html=True)
    users = services.user_repository.list_all()
    for u in users:
        col_name, col_full, col_role, col_shift, col_status, col_edit, col_toggle = st.columns([1.5, 2, 1, 2, 1, 1, 1])
        col_name.write(u.username)
        col_full.write(u.full_name)
        col_role.write(u.role)
        col_shift.write(u.shift_name)
        col_status.write("Active" if u.is_active else "Inactive")
        if col_edit.button("Edit", key=f"edit_user_{u.user_id}"):
            _edit_user_dialog(services, u, shifts)
        disable_self_deactivate = u.username == st.session_state[settings.session_keys.user].username
        if col_toggle.button(
            "Deactivate" if u.is_active else "Activate",
            key=f"toggle_user_{u.user_id}",
            disabled=disable_self_deactivate,
        ):
            services.user_repository.set_active(u.user_id, not u.is_active)
            st.rerun()


@st.dialog("Edit user")
def _edit_user_dialog(services, user, shifts) -> None:
    full_name = st.text_input("Full name", value=user.full_name)
    role = st.selectbox("Role", options=["operator", "admin"], index=["operator", "admin"].index(user.role))
    shift_names = [s.shift_name for s in shifts]
    current_index = shift_names.index(user.shift_name) if user.shift_name in shift_names else 0
    shift_name = st.selectbox("Shift", options=shift_names, index=current_index)
    if st.button("Save changes", type="primary"):
        if not full_name.strip():
            st.error("Full name is required.")
        else:
            role_id = services.user_repository.get_role_id(role)
            shift_id = next(s.shift_id for s in shifts if s.shift_name == shift_name)
            services.user_repository.update_user(user.user_id, full_name.strip(), role_id, shift_id)
            st.rerun()
