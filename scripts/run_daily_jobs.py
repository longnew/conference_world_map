from __future__ import annotations

import argparse
import logging
from pathlib import Path
import sys

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.app.db import init_db
from backend.app.geocoding import geocode_missing
from backend.app.importers import import_sources
from backend.app.llm_extractor import run_llm_extraction


def main() -> None:
    load_dotenv(ROOT / ".env")

    parser = argparse.ArgumentParser(description="Run daily conference tracker jobs.")
    parser.add_argument("--lookahead-years", type=int, default=1)
    parser.add_argument("--geocode-limit", type=int, default=250)
    parser.add_argument("--geocode-sleep", type=float, default=1.0)
    parser.add_argument("--llm-limit", type=int, default=5)
    args = parser.parse_args()

    log_dir = ROOT / "logs"
    log_dir.mkdir(exist_ok=True)
    logging.basicConfig(
        filename=log_dir / "daily_jobs.log",
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )

    init_db()
    logging.info("daily jobs started")
    imported = import_sources(lookahead_years=args.lookahead_years, include_placeholders=False)
    logging.info("source import completed: %s", imported)
    geocoded = geocode_missing(limit=args.geocode_limit, sleep_seconds=args.geocode_sleep)
    logging.info("geocoding completed: %s", geocoded)
    extracted = run_llm_extraction(limit=args.llm_limit)
    logging.info("llm extraction completed: %s", extracted)
    logging.info("daily jobs finished")
    print({"imported": imported, "geocoded": geocoded, "llm_extracted": extracted})


if __name__ == "__main__":
    main()
