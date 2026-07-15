"""
Generate realistic demo data for presentations/demos.

Usage:
    python generate_demo_data.py
    python generate_demo_data.py --batches 10 --inspections-per-batch 20

Never runs automatically — the app starts with only the seeded reference
data (roles, machines, component types, demo accounts). Run this
separately when you want a populated demo scenario.
"""

import argparse
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate demo manufacturing data.")
    parser.add_argument("--batches", type=int, default=6)
    parser.add_argument("--inspections-per-batch", type=int, default=15)
    args = parser.parse_args()

    from app.services import get_services

    services = get_services.__wrapped__()  # bypass st.cache_resource outside Streamlit
    result = services.demo_data_service.generate(
        num_batches=args.batches, inspections_per_batch=args.inspections_per_batch
    )
    print(f"Demo data generated: {result['batches_created']} batches, {result['inspections_created']} inspections.")


if __name__ == "__main__":
    main()
