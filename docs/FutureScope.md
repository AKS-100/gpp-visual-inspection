# Future scope

Deliberately deferred beyond this internship MVP, with the reasoning for
each so the decision reads as intentional rather than an oversight.

## Database extensions

- **`factories` table + `factory_id` on every fact table** — would enable
  multi-plant deployment. Not implemented because GPP operates a single
  facility for this prototype; adding it now would mean every query
  carries an unused filter column.
- **`roles` / `permissions` / `role_permissions` junction** — the current
  `roles` lookup table supports adding a new role name easily, but true
  granular permissions (e.g. "can view dashboard but not manage users")
  would need a permissions table and a many-to-many join. Deferred because
  the MVP only needs two roles with fixed, hardcoded capability checks.
- **`model_component_types` junction** — would let different component
  types route to different specialized AI models, or support A/B testing
  two model versions concurrently. Deferred because the MVP trains one
  general classifier across all five component types.
- **`inspection_stations` as a table separate from `machines`** — would
  model a standalone camera rig decoupled from any single machine.
  Deferred because the MVP's one inspection station is physically
  co-located with a machine.
- **`audit_logs` (generic, polymorphic entity_type/entity_id)** — a full
  security/compliance audit trail across every table. Deferred as
  out-of-scope for an internship prototype's threat model; revisit if
  this becomes a real deployment with compliance requirements.
- **`api_tokens`** — schema-ready for token-based REST API auth. Deferred
  until an actual API layer is built; no consumer exists yet.

## Application features

- Real-time webcam capture for inspection (MVP uses upload only).
- Email/SMS alerting on defect-rate thresholds.
- PDF/Excel report export beyond CSV.
- Production forecasting / predictive maintenance.
- IoT/PLC/MQTT integration for real machine telemetry (current machine
  status is simulated, deterministically, per Architecture.md).
- ERP integration and multi-site synchronization.

## How to extend when the time comes

Each deferred table above is additive — none of them require restructuring
an existing table, only adding a new one and a foreign key. This is a
direct consequence of the repository-pattern boundary established in
Phase 2/4: a new table gets a new repository implementing a new interface,
and existing services are extended to depend on it without needing to be
rewritten.
