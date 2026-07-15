-- ============================================================================
-- GPP Visual Inspection & Manufacturing Analytics -- PostgreSQL schema
-- (Supabase / Streamlit Community Cloud deployment)
-- ============================================================================

CREATE TABLE IF NOT EXISTS roles (
    role_id     SERIAL PRIMARY KEY,
    role_name   TEXT NOT NULL UNIQUE CHECK (role_name IN ('operator', 'admin'))
);

CREATE TABLE IF NOT EXISTS shifts (
    shift_id    SERIAL PRIMARY KEY,
    shift_name  TEXT NOT NULL,
    start_time  TEXT NOT NULL,
    end_time    TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS users (
    user_id         SERIAL PRIMARY KEY,
    username        TEXT NOT NULL UNIQUE,
    password_hash   TEXT NOT NULL,
    salt            TEXT NOT NULL,
    full_name       TEXT NOT NULL,
    role_id         INTEGER NOT NULL REFERENCES roles(role_id) ON DELETE RESTRICT,
    shift_id        INTEGER REFERENCES shifts(shift_id) ON DELETE SET NULL,
    is_active       INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
    created_at      TEXT NOT NULL DEFAULT (NOW()::TEXT)
);

CREATE INDEX IF NOT EXISTS idx_users_role ON users(role_id);

CREATE TABLE IF NOT EXISTS machines (
    machine_id      SERIAL PRIMARY KEY,
    machine_name    TEXT NOT NULL UNIQUE,
    machine_type    TEXT NOT NULL CHECK (
        machine_type IN ('Forge Press', 'CNC Lathe', 'Heat Treatment Furnace', 'Inspection Station', 'Packing Station')
    ),
    default_stage   TEXT NOT NULL CHECK (
        default_stage IN ('Forging', 'Machining', 'Heat Treatment', 'Quality Inspection', 'Packing', 'Dispatch')
    ),
    is_active       INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1))
);

CREATE TABLE IF NOT EXISTS component_types (
    component_id          SERIAL PRIMARY KEY,
    component_name        TEXT NOT NULL UNIQUE,
    description           TEXT,
    target_cycle_time_sec INTEGER,
    is_active             INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1))
);

CREATE TABLE IF NOT EXISTS ai_models (
    model_id          SERIAL PRIMARY KEY,
    model_name        TEXT NOT NULL,
    version           TEXT NOT NULL,
    framework         TEXT NOT NULL DEFAULT 'tensorflow',
    file_path         TEXT NOT NULL,
    is_active         INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
    trained_at        TEXT,
    accuracy_metric   REAL,
    notes             TEXT,
    UNIQUE (model_name, version)
);

CREATE INDEX IF NOT EXISTS idx_ai_models_active ON ai_models(is_active);

CREATE TABLE IF NOT EXISTS production_batches (
    batch_id            SERIAL PRIMARY KEY,
    batch_code          TEXT NOT NULL UNIQUE,
    component_id        INTEGER NOT NULL REFERENCES component_types(component_id) ON DELETE RESTRICT,
    planned_quantity    INTEGER NOT NULL CHECK (planned_quantity > 0),
    actual_quantity     INTEGER NOT NULL DEFAULT 0 CHECK (actual_quantity >= 0),
    current_stage       TEXT NOT NULL DEFAULT 'Forging' CHECK (
        current_stage IN ('Forging', 'Machining', 'Heat Treatment', 'Quality Inspection', 'Packing', 'Dispatch')
    ),
    status              TEXT NOT NULL DEFAULT 'In Progress' CHECK (
        status IN ('In Progress', 'Completed', 'On Hold')
    ),
    created_at          TEXT NOT NULL DEFAULT (NOW()::TEXT),
    updated_at          TEXT NOT NULL DEFAULT (NOW()::TEXT)
);

CREATE INDEX IF NOT EXISTS idx_batches_status_stage ON production_batches(status, current_stage);
CREATE INDEX IF NOT EXISTS idx_batches_component ON production_batches(component_id);

CREATE TABLE IF NOT EXISTS batch_stage_history (
    history_id      SERIAL PRIMARY KEY,
    batch_id        INTEGER NOT NULL REFERENCES production_batches(batch_id) ON DELETE RESTRICT,
    stage           TEXT NOT NULL CHECK (
        stage IN ('Forging', 'Machining', 'Heat Treatment', 'Quality Inspection', 'Packing', 'Dispatch')
    ),
    machine_id      INTEGER REFERENCES machines(machine_id) ON DELETE SET NULL,
    operator_id     INTEGER REFERENCES users(user_id) ON DELETE SET NULL,
    entered_at      TEXT NOT NULL DEFAULT (NOW()::TEXT),
    exited_at       TEXT,
    is_simulated    INTEGER NOT NULL DEFAULT 1 CHECK (is_simulated IN (0, 1))
);

CREATE INDEX IF NOT EXISTS idx_stage_history_batch ON batch_stage_history(batch_id);

CREATE TABLE IF NOT EXISTS defect_types (
    defect_id     SERIAL PRIMARY KEY,
    defect_name   TEXT NOT NULL UNIQUE,
    description   TEXT,
    severity      TEXT NOT NULL DEFAULT 'moderate' CHECK (severity IN ('minor', 'moderate', 'critical'))
);

CREATE TABLE IF NOT EXISTS inspections (
    inspection_id           SERIAL PRIMARY KEY,
    batch_id                INTEGER NOT NULL REFERENCES production_batches(batch_id) ON DELETE RESTRICT,
    component_id            INTEGER NOT NULL REFERENCES component_types(component_id) ON DELETE RESTRICT,
    machine_id              INTEGER REFERENCES machines(machine_id) ON DELETE SET NULL,
    operator_id             INTEGER NOT NULL REFERENCES users(user_id) ON DELETE RESTRICT,
    shift_id                INTEGER REFERENCES shifts(shift_id) ON DELETE SET NULL,
    model_id                INTEGER REFERENCES ai_models(model_id) ON DELETE SET NULL,
    model_version_snapshot  TEXT NOT NULL,
    image_path              TEXT NOT NULL,
    heatmap_path            TEXT,
    prediction              TEXT NOT NULL CHECK (prediction IN ('GOOD', 'DEFECTIVE')),
    confidence_score        REAL NOT NULL CHECK (confidence_score >= 0 AND confidence_score <= 1),
    inspected_at            TEXT NOT NULL DEFAULT (NOW()::TEXT)
);

CREATE INDEX IF NOT EXISTS idx_inspections_batch ON inspections(batch_id);
CREATE INDEX IF NOT EXISTS idx_inspections_inspected_at ON inspections(inspected_at);
CREATE INDEX IF NOT EXISTS idx_inspections_operator ON inspections(operator_id);

CREATE TABLE IF NOT EXISTS inspection_defects (
    inspection_id   INTEGER NOT NULL REFERENCES inspections(inspection_id) ON DELETE CASCADE,
    defect_id       INTEGER NOT NULL REFERENCES defect_types(defect_id) ON DELETE RESTRICT,
    PRIMARY KEY (inspection_id, defect_id)
);

CREATE TABLE IF NOT EXISTS production_log (
    log_id          SERIAL PRIMARY KEY,
    machine_id      INTEGER NOT NULL REFERENCES machines(machine_id) ON DELETE RESTRICT,
    shift_id        INTEGER REFERENCES shifts(shift_id) ON DELETE SET NULL,
    batch_id        INTEGER REFERENCES production_batches(batch_id) ON DELETE SET NULL,
    log_date        TEXT NOT NULL,
    units_produced  INTEGER NOT NULL DEFAULT 0 CHECK (units_produced >= 0),
    units_rejected  INTEGER NOT NULL DEFAULT 0 CHECK (units_rejected >= 0),
    is_simulated    INTEGER NOT NULL DEFAULT 1 CHECK (is_simulated IN (0, 1))
);

CREATE INDEX IF NOT EXISTS idx_production_log_date ON production_log(log_date);

CREATE TABLE IF NOT EXISTS machine_status_log (
    log_id          SERIAL PRIMARY KEY,
    machine_id      INTEGER NOT NULL REFERENCES machines(machine_id) ON DELETE RESTRICT,
    status          TEXT NOT NULL CHECK (status IN ('Running', 'Idle', 'Maintenance')),
    logged_at       TEXT NOT NULL DEFAULT (NOW()::TEXT),
    is_simulated    INTEGER NOT NULL DEFAULT 1 CHECK (is_simulated IN (0, 1))
);

CREATE INDEX IF NOT EXISTS idx_machine_status_machine_time ON machine_status_log(machine_id, logged_at);

CREATE TABLE IF NOT EXISTS reports (
    report_id           SERIAL PRIMARY KEY,
    generated_by        INTEGER NOT NULL REFERENCES users(user_id) ON DELETE RESTRICT,
    report_type         TEXT NOT NULL,
    date_range_start    TEXT NOT NULL,
    date_range_end      TEXT NOT NULL,
    file_path           TEXT NOT NULL,
    generated_at        TEXT NOT NULL DEFAULT (NOW()::TEXT)
);

CREATE TABLE IF NOT EXISTS app_settings (
    setting_key     TEXT PRIMARY KEY,
    setting_value   TEXT NOT NULL,
    updated_at      TEXT NOT NULL DEFAULT (NOW()::TEXT),
    updated_by      INTEGER REFERENCES users(user_id) ON DELETE SET NULL
);
