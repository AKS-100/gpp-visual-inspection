# Architecture

## System overview

The application is split into two coupled subsystems sharing one database:

- **Inspection engine** — image in, preprocessing (OpenCV), CNN classification
  (transfer-learning MobileNetV2), Grad-CAM overlay, result persisted against
  a production batch.
- **Manufacturing analytics platform** — every persisted inspection and every
  simulated production event feeds the Factory Overview digital twin and the
  KPI dashboard.

## Layering

```
Presentation (Streamlit pages)
      -> Service layer (core/services)
            -> ML/CV layer (core/ml)   AND   Data access layer (core/repositories)
                  -> SQLite database
```

Pages never query the database or call the ML model directly — they call a
service, which is the only layer allowed to touch a repository or the model
registry. This is the boundary that makes "swap SQLite for Postgres" or "swap
the classifier for a new model version" a one-file change instead of a
grep-and-replace across the app.

## Real vs simulated data — structural separation

`InspectionService` is the only code path that writes to `inspections` /
`inspection_defects`, and every write originates from a real image run
through the model. `SimulationService` is the only code path that writes to
production-lifecycle and machine-status tables for stages that aren't backed
by a real dataset (Forging, Machining, Heat Treatment). These are separate
services with no shared write path — "real vs simulated" is enforced by
which table the data lives in, not by a convention someone could forget.

Simulated factory state is a **pure function of the current time**, seeded
deterministically per day, rather than a mutated stored value — so a page
refresh always shows consistent, plausible state with no background process
required.

## Folder structure

See the repository root for the live structure. Summary of responsibilities:

| Path | Responsibility |
|---|---|
| `app/` | Streamlit presentation layer: pages, reusable components, theme |
| `core/services/` | Business logic the UI calls into |
| `core/repositories/` | Data-access layer, one interface + implementation per aggregate |
| `core/ml/` | Preprocessing, inference, Grad-CAM (added Phase 6/7) |
| `database/` | Schema, connection management, migrations |
| `ml_pipeline/` | Offline training code — never imported by the running app |
| `config/` | Centralized settings, no literals scattered through the codebase |
| `docs/` | This documentation set |

## Deliberate scope decisions

- Production lifecycle is an append-only history log, not a governed
  workflow/state-machine engine.
- Auth is salted-hash + session role gating, not a full RBAC/JWT system —
  though the database schema (see Database.md) is ready for that to grow.
- No real-time background processes; simulated "live" state is derived per
  request, not streamed.

See FutureScope.md for what was deliberately cut from this internship build
and where the schema/architecture already anticipates it.
