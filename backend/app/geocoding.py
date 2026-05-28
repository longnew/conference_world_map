from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any

import httpx

from .db import connect, dumps, loads

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
USER_AGENT = "conference-map/0.1 (local research conference tracker)"


def ensure_geocode_cache(conn) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS geocode_cache (
            query TEXT PRIMARY KEY,
            latitude REAL,
            longitude REAL,
            display_name TEXT,
            precision TEXT NOT NULL,
            provider TEXT NOT NULL,
            raw_json TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )


def geocode_query(client: httpx.Client, query: str) -> dict[str, Any] | None:
    response = client.get(
        NOMINATIM_URL,
        params={"q": query, "format": "jsonv2", "limit": 1},
        headers={"User-Agent": USER_AGENT},
    )
    response.raise_for_status()
    results = response.json()
    if not results:
        return None
    result = results[0]
    return {
        "latitude": float(result["lat"]),
        "longitude": float(result["lon"]),
        "display_name": result.get("display_name"),
        "precision": "city_center",
        "provider": "nominatim",
        "raw": result,
    }


def build_query(row: dict[str, Any]) -> str | None:
    if row.get("venue_name") and row.get("city") and row.get("country"):
        return f"{row['venue_name']}, {row['city']}, {row['country']}"
    if row.get("city") and row.get("country"):
        return f"{row['city']}, {row['country']}"
    if row.get("city"):
        return row["city"]
    return None


def geocode_missing(limit: int | None = None, sleep_seconds: float = 1.0) -> dict[str, int]:
    updated = 0
    skipped = 0
    failed = 0
    now = datetime.now(timezone.utc).isoformat()

    with connect() as conn:
        ensure_geocode_cache(conn)
        query = """
            SELECT instance_id, venue_name, city, state_or_region, country
            FROM instances
            WHERE latitude IS NULL AND longitude IS NULL AND city IS NOT NULL
            ORDER BY year, instance_id
        """
        rows = [dict(row) for row in conn.execute(query).fetchall()]
        if limit is not None:
            rows = rows[:limit]

        with httpx.Client(timeout=30.0, follow_redirects=True) as client:
            for row in rows:
                geocode_text = build_query(row)
                if not geocode_text:
                    skipped += 1
                    continue

                cached = conn.execute("SELECT * FROM geocode_cache WHERE query = ?", [geocode_text]).fetchone()
                if cached:
                    result = {
                        "latitude": cached["latitude"],
                        "longitude": cached["longitude"],
                        "precision": cached["precision"],
                        "display_name": cached["display_name"],
                        "raw": loads(cached["raw_json"], {}),
                    }
                else:
                    try:
                        result = geocode_query(client, geocode_text)
                    except Exception:
                        failed += 1
                        time.sleep(sleep_seconds)
                        continue

                    if result is None:
                        failed += 1
                        conn.execute(
                            """
                            INSERT OR REPLACE INTO geocode_cache (
                                query, latitude, longitude, display_name, precision,
                                provider, raw_json, updated_at
                            )
                            VALUES (?, NULL, NULL, NULL, 'unknown', 'nominatim', '{}', ?)
                            """,
                            [geocode_text, now],
                        )
                        time.sleep(sleep_seconds)
                        continue

                    conn.execute(
                        """
                        INSERT OR REPLACE INTO geocode_cache (
                            query, latitude, longitude, display_name, precision,
                            provider, raw_json, updated_at
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        [
                            geocode_text,
                            result["latitude"],
                            result["longitude"],
                            result["display_name"],
                            result["precision"],
                            result["provider"],
                            dumps(result["raw"]),
                            now,
                        ],
                    )
                    time.sleep(sleep_seconds)

                if result["latitude"] is None or result["longitude"] is None:
                    failed += 1
                    continue

                conn.execute(
                    """
                    UPDATE instances
                    SET latitude = ?, longitude = ?, coordinate_precision = ?,
                        updated_at = ?
                    WHERE instance_id = ?
                    """,
                    [
                        result["latitude"],
                        result["longitude"],
                        result["precision"],
                        now,
                        row["instance_id"],
                    ],
                )
                updated += 1

    return {"updated": updated, "skipped": skipped, "failed": failed}
