from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.app.countries import normalize_country
from backend.app.db import connect


def main() -> None:
    changed = 0
    with connect() as conn:
        rows = conn.execute("SELECT instance_id, country FROM instances WHERE country IS NOT NULL").fetchall()
        for row in rows:
            normalized = normalize_country(row["country"])
            if normalized and normalized != row["country"]:
                conn.execute(
                    "UPDATE instances SET country = ? WHERE instance_id = ?",
                    [normalized, row["instance_id"]],
                )
                changed += 1
    print(f"Normalized countries on {changed} instances.")


if __name__ == "__main__":
    main()
