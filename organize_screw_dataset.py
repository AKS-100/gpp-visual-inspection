from pathlib import Path
import shutil
import pandas as pd

ROOT = Path(__file__).parent

ARCHIVE = ROOT / "data" / "archive"
TRAIN_IMAGES = ARCHIVE / "train"
CSV_FILE = ARCHIVE / "train.csv"

DEST = ROOT / "data" / "screw_dataset"

GOOD_DIR = DEST / "all" / "good"
BAD_DIR = DEST / "all" / "defective"

GOOD_DIR.mkdir(parents=True, exist_ok=True)
BAD_DIR.mkdir(parents=True, exist_ok=True)

df = pd.read_csv(CSV_FILE)

good = 0
bad = 0

for _, row in df.iterrows():
    src = TRAIN_IMAGES / row["filename"]

    if not src.exists():
        continue

    if int(row["anomaly"]) == 0:
        shutil.copy2(src, GOOD_DIR / src.name)
        good += 1
    else:
        shutil.copy2(src, BAD_DIR / src.name)
        bad += 1

print(f"Copied {good} good and {bad} defective images.")