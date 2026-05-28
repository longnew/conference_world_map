from __future__ import annotations

import argparse
from pathlib import Path
import sys

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.app.db import init_db
from backend.app.llm_extractor import run_llm_extraction


def main() -> None:
    load_dotenv(ROOT / ".env")

    parser = argparse.ArgumentParser(description="Run LLM official-page extraction.")
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--model", default=None)
    args = parser.parse_args()

    init_db()
    print(run_llm_extraction(limit=args.limit, model=args.model))


if __name__ == "__main__":
    main()
