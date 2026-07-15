# GPP Visual Inspection & Manufacturing Analytics

AI-powered visual quality inspection and manufacturing analytics platform
built as a 30-day industrial internship prototype for **Ghaziabad
Precision Products Pvt. Ltd.** — an Industry 4.0 quality-inspection and
production-tracking system for precision automotive components (Push
Rod, Rocker Arm, Valve Bridge, Tappet, Injector Clamp).

## What it does

- **Inspection engine**: upload a component image, an EfficientNetB0
  classifier (transfer-learned) predicts GOOD/DEFECTIVE with a confidence
  score and a Grad-CAM heatmap.
- **Manufacturing analytics**: a live factory-status dashboard, batch
  lifecycle tracking (Forging → Machining → Heat Treatment → Quality
  Inspection → Packing → Dispatch), searchable inspection history, and
  CSV/PDF reporting.

## Architecture

```
Presentation (Streamlit pages)
      -> Service layer (core/services) — all business logic
            -> ML/CV layer (core/ml)     Data access layer (core/repositories)
                  -> SQLite database
```

Pages never touch the database or the ML model directly — every read/write
goes through a service, which is the only layer allowed to call a
repository or the model registry. Full rationale in `docs/Architecture.md`.

## Folder structure

```
app/                  Streamlit UI: pages, reusable components, design-system theme
core/
  services/           Business logic (batch lifecycle, inspection workflow, dashboard KPIs, reports)
  repositories/        Data access — one interface + SQLite implementation per aggregate
  ml/                  Inference interface, preprocessing, training, Grad-CAM, evaluation
database/              schema.sql, connection manager, seed data
ml_pipeline/           Offline training entrypoint (never imported by the running app)
config/                Centralized settings — no hardcoded literals elsewhere
docs/                  Architecture, database, ML pipeline, UI guidelines, user guide, deployment
exports/               Generated CSV/PDF reports
```

## Installation

```bash
pip install -r requirements.txt
python database/seed_data.py
streamlit run app/main.py
```

Full details: `docs/Installation.md`.

## Demo credentials

| Role | Username | Password |
|---|---|---|
| Operator | `operator1` | `operator123` |
| Admin | `admin1` | `admin123` |

Change or remove these before any real deployment.

## Optional: populate demo data

```bash
python generate_demo_data.py --batches 6 --inspections-per-batch 15
```

## Training the real model

The app runs on a deterministic `DummyInferenceEngine` until a trained
model exists — no setup required to explore the full application.

```bash
python ml_pipeline/train.py --datasets screw casting --epochs 20 --fine-tune-epochs 10
```

Once `models/industrial_quality_classifier.keras` exists, the app
automatically switches to `TensorFlowInferenceEngine` on next restart —
no code changes needed. Full details: `docs/ML_Pipeline.md`.

## Documentation

| Doc | Covers |
|---|---|
| `docs/Architecture.md` | Layering, real-vs-simulated data separation, scope decisions |
| `docs/Database.md` | Schema, constraints, indexes, ER design rationale |
| `docs/ML_Pipeline.md` | Dataset strategy, model choice, training workflow, known limitations |
| `docs/UI_Guidelines.md` | Design system tokens, component library |
| `docs/ProjectFlow.md` | End-to-end workflow, phase history |
| `docs/UserGuide.md` | How to use every page |
| `docs/Installation.md` / `Deployment.md` | Setup and deployment path |
| `docs/FutureScope.md` | What was deliberately deferred, and why |

## Future scope

Multi-factory support, granular role/permission management, per-component
AI model routing, REST API layer, real machine telemetry (current
utilization is a stage-history-based proxy metric), multi-class defect
typing. All documented in detail in `docs/FutureScope.md` — deferred
deliberately, not overlooked.

## Screenshots

_Add screenshots to `docs/Screenshots/` — Factory Overview, Inspection
workflow with Grad-CAM, Dashboard, Batches, Admin._
