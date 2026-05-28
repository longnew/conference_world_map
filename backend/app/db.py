from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data"
DB_PATH = DATA_DIR / "conference_map.sqlite3"
SEED_PATH = DATA_DIR / "seed_data.json"


def connect() -> sqlite3.Connection:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False)


def loads(value: str | None, fallback: Any) -> Any:
    if not value:
        return fallback
    return json.loads(value)


def init_db() -> None:
    with connect() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS conferences (
                conference_id TEXT PRIMARY KEY,
                abbreviation TEXT NOT NULL,
                full_name TEXT NOT NULL,
                homepage_root TEXT,
                ranking_json TEXT NOT NULL,
                primary_category TEXT NOT NULL,
                secondary_categories_json TEXT NOT NULL,
                purpose_summary TEXT NOT NULL,
                known_series_pattern TEXT NOT NULL,
                typical_months_json TEXT NOT NULL,
                tracking_priority TEXT NOT NULL,
                source_urls_json TEXT NOT NULL,
                active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS instances (
                instance_id TEXT PRIMARY KEY,
                conference_id TEXT NOT NULL REFERENCES conferences(conference_id),
                year INTEGER NOT NULL,
                official_website TEXT,
                website_status TEXT NOT NULL,
                event_status TEXT NOT NULL,
                start_date TEXT,
                end_date TEXT,
                timezone TEXT,
                city TEXT,
                state_or_region TEXT,
                country TEXT,
                venue_name TEXT,
                latitude REAL,
                longitude REAL,
                coordinate_precision TEXT NOT NULL DEFAULT 'unknown',
                submission_deadline TEXT,
                abstract_deadline TEXT,
                notification_date TEXT,
                camera_ready_deadline TEXT,
                registration_deadline TEXT,
                last_checked_at TEXT,
                next_check_at TEXT,
                confidence TEXT NOT NULL,
                evidence_json TEXT NOT NULL,
                notes TEXT,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS update_history (
                history_id TEXT PRIMARY KEY,
                instance_id TEXT NOT NULL REFERENCES instances(instance_id),
                field TEXT NOT NULL,
                old_value TEXT,
                new_value TEXT,
                source_url TEXT,
                updated_at TEXT NOT NULL,
                update_method TEXT NOT NULL,
                confidence TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS conflicts (
                conflict_id TEXT PRIMARY KEY,
                instance_id TEXT NOT NULL REFERENCES instances(instance_id),
                field TEXT NOT NULL,
                values_json TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'open',
                created_at TEXT NOT NULL,
                resolved_at TEXT
            );

            CREATE TABLE IF NOT EXISTS deadline_events (
                deadline_id TEXT PRIMARY KEY,
                instance_id TEXT NOT NULL REFERENCES instances(instance_id),
                deadline_type TEXT NOT NULL,
                deadline_date TEXT,
                deadline_time_raw TEXT,
                timezone TEXT,
                comment TEXT,
                source_url TEXT,
                confidence TEXT NOT NULL,
                evidence_json TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            """
        )
        seed_if_empty(conn)


def seed_if_empty(conn: sqlite3.Connection) -> None:
    existing = conn.execute("SELECT COUNT(*) AS n FROM conferences").fetchone()["n"]
    if existing:
        return

    seed = json.loads(SEED_PATH.read_text(encoding="utf-8"))
    for row in seed["conferences"]:
        conn.execute(
            """
            INSERT INTO conferences VALUES (
                :conference_id, :abbreviation, :full_name, :homepage_root,
                :ranking_json, :primary_category, :secondary_categories_json,
                :purpose_summary, :known_series_pattern, :typical_months_json,
                :tracking_priority, :source_urls_json, :active, :created_at, :updated_at
            )
            """,
            {
                **row,
                "ranking_json": dumps(row["ranking"]),
                "secondary_categories_json": dumps(row["secondary_categories"]),
                "typical_months_json": dumps(row["typical_months"]),
                "source_urls_json": dumps(row["source_urls"]),
                "active": 1 if row.get("active", True) else 0,
            },
        )

    for row in seed["instances"]:
        conn.execute(
            """
            INSERT INTO instances VALUES (
                :instance_id, :conference_id, :year, :official_website,
                :website_status, :event_status, :start_date, :end_date, :timezone,
                :city, :state_or_region, :country, :venue_name, :latitude, :longitude,
                :coordinate_precision, :submission_deadline, :abstract_deadline,
                :notification_date, :camera_ready_deadline, :registration_deadline,
                :last_checked_at, :next_check_at, :confidence, :evidence_json,
                :notes, :updated_at
            )
            """,
            {**row, "evidence_json": dumps(row.get("evidence", []))},
        )


def rows(query: str, params: Iterable[Any] = ()) -> list[dict[str, Any]]:
    with connect() as conn:
        return [dict(row) for row in conn.execute(query, tuple(params)).fetchall()]


def row(query: str, params: Iterable[Any] = ()) -> dict[str, Any] | None:
    with connect() as conn:
        found = conn.execute(query, tuple(params)).fetchone()
        return dict(found) if found else None
