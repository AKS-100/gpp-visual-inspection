from pathlib import Path
import shutil
import random

ROOT = Path(__file__).parent

SOURCE = ROOT / "data" / "archive (1)" / "casting_data" / "casting_data"
DEST = ROOT / "data" / "casting_dataset"

random.seed(42)

classes = {
    "ok_front": "good",
    "def_front": "defective",
}

for split in ["train", "validation", "test"]:
    for cls in classes.values():
        (DEST / split / cls).mkdir(parents=True, exist_ok=True)


def copy_split(split_name):
    for source_name, target_name in classes.items():

        files = list((SOURCE / split_name / source_name).glob("*.*"))
        random.shuffle(files)

        if split_name == "train":
            val_size = int(len(files) * 0.2)

            val = files[:val_size]
            train = files[val_size:]

            for f in train:
                shutil.copy2(f, DEST / "train" / target_name / f.name)

            for f in val:
                shutil.copy2(f, DEST / "validation" / target_name / f.name)

        else:
            for f in files:
                shutil.copy2(f, DEST / "test" / target_name / f.name)


copy_split("train")
copy_split("test")

print("\n========== CASTING DATASET READY ==========\n")

for cls in ["good", "defective"]:
    print(cls.upper())

    for split in ["train", "validation", "test"]:
        count = len(list((DEST / split / cls).glob("*.*")))
        print(split, count)

    print()