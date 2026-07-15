# Database

Status: **implemented (Phase 4), MVP scope.**

## Scope note

An earlier design pass (documented in chat, Phase 4 planning) explored a
fully future-proofed schema with multi-factory support, a granular
roles/permissions junction, per-component AI model routing, standalone
inspection stations, generic audit logging, and API tokens. That version
was deliberately **not implemented**. This MVP implements exactly the
15 tables needed by the current application and the two systems it
supports (Inspection engine, Manufacturing analytics dashboard); everything
else from that exploration is documented in FutureScope.md as a schema
extension path, not built ahead of need.

## Tables

**Identity & scheduling**
- `roles` — lookup table (`operator`, `admin`). A table rather than a
  string column so a future third role is a data change, not a schema
  change.
- `shifts` — shift name and time window. Referenced by `users` and used
  for shift-wise analytics.
- `users` — credentials (PBKDF2 hash + salt), full name, role, shift,
  active flag.

**Manufacturing floor**
- `machines` — name, type (`CHECK`-constrained to five known categories),
  default production stage.
- `component_types` — the five GPP products (Push Rod, Rocker Arm, Valve
  Bridge, Tappet, Injector Clamp). The application is component-agnostic:
  adding a sixth product is a row insert, not a code change.

**AI model registry**
- `ai_models` — name, version, framework, file path, active flag, accuracy
  metric. MVP scope keeps exactly one active model shared across all
  component types; per-component model routing is deferred (see
  FutureScope.md) since nothing today needs more than one active model.

**Production batches & lifecycle**
- `production_batches` — batch code, component, planned/actual quantity,
  current stage, status.
- `batch_stage_history` — append-only log of stage transitions. Modeled as
  a history log, not a governed workflow engine, per the Phase 2
  architecture decision to keep lifecycle tracking observational rather
  than rule-enforcing at this scope.

**Inspections & defects**
- `defect_types` — name, description, severity.
- `inspections` — one row per AI inspection: batch, component, machine,
  operator, shift, which model produced it (`model_id`, nullable) plus a
  `model_version_snapshot` string that is preserved even if the model
  registry row is later deleted or deprecated — this is what keeps
  inspection history meaningful independent of model registry churn.
- `inspection_defects` — many-to-many between inspections and defect
  types (a single defective part can show more than one defect).

**Simulated production data** (structurally separate from real inspection
data — see Architecture.md)
- `production_log` — daily units produced/rejected per machine, flagged
  `is_simulated`.
- `machine_status_log` — machine status history, flagged `is_simulated`.

**Reports & settings**
- `reports` — metadata for generated reports (type, date range, file path).
- `app_settings` — key/value store for admin-configurable values
  (confidence threshold, batch-stage-advance unit count) so these aren't
  hardcoded constants.

## Constraints and indexes

- Every enum-like column (`role_name`, `machine_type`, `default_stage`,
  `current_stage`, `status`, `prediction`, `severity`) uses a SQLite
  `CHECK` constraint rather than relying on application code alone to
  keep values valid.
- Foreign keys default to `ON DELETE RESTRICT` — you cannot delete a
  machine, component type, or defect type that has inspection history
  without first archiving it (`is_active = 0`). The one intentional
  exception is `inspections.model_id`, which uses `ON DELETE SET NULL`
  paired with the `model_version_snapshot` string column.
- Indexes: `users.username` (unique), `production_batches.batch_code`
  (unique), `production_batches(status, current_stage)` (composite —
  supports the Batches page's primary query), `inspections(batch_id)`,
  `inspections(inspected_at)`, `inspections(operator_id)`,
  `machine_status_log(machine_id, logged_at)`, `production_log(log_date)`.

## SQLite-specific implementation notes

- SQLite does not enforce foreign keys unless `PRAGMA foreign_keys = ON`
  is set **per connection**. `database/db_manager.get_connection()` sets
  this on every connection it opens — verified by an explicit test during
  Phase 4 implementation (see git history / chat log) that confirmed a
  bad foreign key actually raises `IntegrityError` rather than silently
  succeeding.
- Multi-statement writes (an inspection plus its defect links; a batch's
  stage update plus its history row) go through
  `database.db_manager.transaction()`, a context manager that commits on
  success and rolls back on any exception — verified with a deliberate
  bad-input test that confirmed a failed defect insert rolls back the
  inspection insert too, rather than leaving a partial row.

## Seed data

`database/seed_data.py` is idempotent (`INSERT OR IGNORE` / unique
constraints) and seeds: 2 roles, 3 shifts, 2 demo users (`operator1` /
`admin1`), 5 machines, 5 component types, 5 defect types, 1 AI model
registry entry, and default app settings. Demo user passwords are hashed
through `AuthService.hash_password` at seed time — there are no
hand-computed hash strings to keep in sync.

## Repository layer

Every table with an application consumer has a corresponding repository
in `core/repositories/`, each with an interface class and a `Sqlite*`
implementation: `SqliteUserRepository`, `SqliteMachineRepository`,
`SqliteComponentTypeRepository`, `SqliteDefectTypeRepository`,
`SqliteAiModelRepository`, `SqliteBatchRepository`,
`SqliteInspectionRepository`, `SqliteReportRepository`,
`SqliteSettingsRepository`. `core/repositories/base_repository.py` holds
shared connection-handling boilerplate so each repository file contains
only its own domain logic and SQL.
