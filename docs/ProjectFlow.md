# Project Flow

## End-to-end workflow
```
Login (role-gated)
   |
Factory Overview (landing page — live status)
   |
Batches: create batch -> advance Forging -> Machining -> Heat Treatment
   |
Inspection: select batch (must be at Quality Inspection) -> select machine
   -> upload image -> AI prediction -> save -> batch inspection count++
   |
   (auto) enough inspections reached -> batch advances to Packing -> Dispatch
   |
Dashboard / History: analytics and searchable record of every inspection
   |
Reports: CSV/PDF export of the full picture (summary, defects, machines, batches)
```

## Development phases (as built)
1. Requirements analysis & architecture
2. Software architecture (layered: UI -> services -> repositories -> DB)
3. UI/UX design system (SCADA-inspired, dark industrial + warm metallic)
4. Database implementation (SQLite, 15 tables, repository pattern)
5. Service layer (business logic, dependency-inverted from repositories)
6. UI integration (all 7 pages wired to real services)
7. ML pipeline (EfficientNetB0, dataset adapters, Grad-CAM, drop-in inference engine)
8. Polish (Plotly analytics, error handling, admin CRUD, report export, demo data, docs)

## Key architectural decisions
- Real inspection data and simulated pre-QI production data are
  structurally separated (different services, different write paths) — see Architecture.md.
- `AIInferenceEngine` is a Protocol; `DummyInferenceEngine` and
  `TensorFlowInferenceEngine` are interchangeable with zero changes to
  `InspectionService`.
- Batch lifecycle is a strictly linear, append-only history log — no
  rework loops in this MVP (see FutureScope.md).
