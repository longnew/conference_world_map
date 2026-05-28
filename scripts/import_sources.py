from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.app.db import init_db
from backend.app.importers import import_sources


def main() -> None:
    parser = argparse.ArgumentParser(description="Import CCF/KIISE conference seed sources.")
    parser.add_argument("--lookahead-years", type=int, default=1)
    parser.add_argument(
        "--include-placeholders",
        action="store_true",
        help="Generate empty future-year placeholders. Off by default.",
    )
    args = parser.parse_args()

    init_db()
    result = import_sources(
        lookahead_years=args.lookahead_years,
        include_placeholders=args.include_placeholders,
    )
    print(f"Imported {result['conferences']} conferences and {result['instances']} rolling instances.")


if __name__ == "__main__":
    main()
