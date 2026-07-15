# Installation

## Prerequisites
- Python 3.10+
- pip

## Setup
```bash
git clone <repo-url>
cd gpp-visual-inspection
pip install -r requirements.txt
```

## Initialize the database
```bash
python database/seed_data.py
```
Creates `database/gpp_inspection.db` with reference data (roles, shifts,
machines, component types, defect types, demo accounts) if it doesn't
already exist. Safe to re-run — idempotent.

## (Optional) Generate demo data
```bash
python generate_demo_data.py --batches 6 --inspections-per-batch 15
```

## Run the app
```bash
streamlit run app/main.py
```
Open the URL Streamlit prints (default `http://localhost:8501`).

## (Optional) Train the real ML model
See `docs/ML_Pipeline.md` for dataset setup and training commands.
Without a trained model, the app uses `DummyInferenceEngine` automatically.
