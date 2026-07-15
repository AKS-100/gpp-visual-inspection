# User Guide

## Logging in
Demo accounts (change before any real deployment):
- Operator: `operator1` / `operator123`
- Admin: `admin1` / `admin123`

## Running an inspection
1. Open **Inspection**.
2. Select a batch (only batches at the *Quality Inspection* stage appear).
3. Select the inspection machine.
4. Upload a component image.
5. Click **Run AI inspection**. Result, confidence, and (once a trained
   model is active) a Grad-CAM heatmap appear below.
6. The result is saved automatically and counted toward the batch's
   inspection total. Once enough inspections are recorded (see Settings),
   the batch automatically advances to Packing.

## Tracking batches
**Batches** shows every batch's stage, completion %, current machine, and
full stage history. Admins/operators advance a batch to its next stage
with the **Advance to...** button — only the next legal stage is offered.

## Reviewing history
**History** supports filtering by batch code, result, date range,
machine, component, and confidence range, with image/heatmap preview per
record.

## Dashboards
**Factory Overview** is the landing page — live machine status, active
batches, and today's numbers. **Dashboard** has full analytics: trends,
defect breakdown, utilization, confidence distribution, and CSV/PDF
export.

## Administration (admin accounts only)
**Admin**: manage machines, component types, AI models, and users
(create, edit, activate/deactivate). **Settings**: confidence threshold
and the inspection-count threshold that triggers automatic batch
progression — changes apply immediately, no restart needed.
