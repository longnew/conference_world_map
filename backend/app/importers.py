from __future__ import annotations

import csv
import io
import re
import uuid
from datetime import date, datetime, timedelta, timezone
from typing import Any

import httpx
import yaml

from .countries import normalize_country
from .db import connect, dumps, loads

KIISE_GIST_RAW_URL = "https://gist.github.com/Pusnow/6eb933355b5cb8d31ef1abcb3c3e1206/raw/"
CCFDDL_TREE_URL = "https://api.github.com/repos/ccfddl/ccf-deadlines/git/trees/main?recursive=1"
CCFDDL_RAW_BASE = "https://raw.githubusercontent.com/ccfddl/ccf-deadlines/main"

SOURCE_CCFDDL = "https://github.com/ccfddl/ccf-deadlines"
SOURCE_CCFDDL_SITE = "https://ccfddl.com/"

MONTHS = {
    "jan": 1,
    "january": 1,
    "feb": 2,
    "february": 2,
    "mar": 3,
    "march": 3,
    "apr": 4,
    "april": 4,
    "may": 5,
    "jun": 6,
    "june": 6,
    "jul": 7,
    "july": 7,
    "aug": 8,
    "august": 8,
    "sep": 9,
    "sept": 9,
    "september": 9,
    "oct": 10,
    "october": 10,
    "nov": 11,
    "november": 11,
    "dec": 12,
    "december": 12,
}

SUB_TO_CATEGORY = {
    "AI": "AI / Machine Learning",
    "CG": "HCI / Visualization",
    "CT": "Algorithms / Theory",
    "DB": "Database / Data Engineering",
    "DS": "Computer Architecture",
    "HI": "HCI / Visualization",
    "MX": "Interdiscipline / Emerging",
    "NW": "Networking",
    "SC": "Security / Privacy",
    "SE": "Software Engineering",
}

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalize_abbreviation(value: str) -> str:
    value = re.sub(r"\s*\((oral|poster|spotlight)\)\s*", "", value, flags=re.I)
    value = value.replace("NeurIPS/NIPS", "NeurIPS")
    value = value.replace("NIPS", "NeurIPS")
    value = value.replace("VLDB / PVLDB", "VLDB")
    value = value.replace("ICSME (ICSM)", "ICSME")
    value = value.replace("EuroS&P", "EuroS&P")
    return value.strip()


def conference_id(value: str) -> str:
    normalized = normalize_abbreviation(value).lower()
    normalized = normalized.replace("&", "and").replace("+", " plus ")
    normalized = re.sub(r"[^a-z0-9]+", "-", normalized)
    return normalized.strip("-")


def clean_full_name(value: str, abbreviation: str) -> str:
    value = re.sub(r"\s*\((oral|poster|spotlight)\)\s*", "", value, flags=re.I)
    value = re.sub(rf"\s*\({re.escape(abbreviation)}\)\s*$", "", value, flags=re.I)
    return value.strip()


def fetch_text(url: str) -> str:
    with httpx.Client(timeout=30.0, follow_redirects=True) as client:
        response = client.get(url, headers={"User-Agent": "conference-map-importer/0.1"})
        response.raise_for_status()
        return response.text


def fetch_kiise_rows(url: str = KIISE_GIST_RAW_URL) -> dict[str, dict[str, Any]]:
    content = fetch_text(url)
    reader = csv.DictReader(io.StringIO(content))
    rows: dict[str, dict[str, Any]] = {}

    for raw in reader:
        kiise = (raw.get("한국정보과학회 (2024)") or "").strip()
        postech = (raw.get("POSTECH CSE (2026.1)") or "").strip()
        if kiise not in {"최우수", "우수"} and postech not in {"최우수", "우수"}:
            continue

        abbreviation = normalize_abbreviation(raw["약자"])
        cid = conference_id(abbreviation)
        best_kiise = "최우수" if "최우수" in {kiise, postech} else "우수"
        current = rows.get(cid)
        if current and current["kiise"] == "최우수":
            continue

        rows[cid] = {
            "conference_id": cid,
            "abbreviation": abbreviation,
            "kiise": best_kiise,
            "full_name": clean_full_name(raw["학회명"], abbreviation),
            "dblp_key": (raw.get("DBLP Key") or "").strip(),
            "source_url": url,
            "source_metadata": {
                "bk21_if_2018": (raw.get("BK21플러스 IF (2018)") or "").strip(),
                "kaist_cs_2022": (raw.get("KAIST CS (2022)") or "").strip(),
                "snu_cse_2024_04": (raw.get("SNU CSE (2024.4)") or "").strip(),
                "postech_cse_2026_01": postech,
                "average_normalized": (raw.get("평균 (정규화)") or "").strip(),
            },
        }

    return rows


def fetch_ccfddl_entries() -> dict[str, dict[str, Any]]:
    tree = httpx.get(CCFDDL_TREE_URL, timeout=30.0).json()["tree"]
    paths = [
        item["path"]
        for item in tree
        if item["path"].startswith("conference/")
        and item["path"].endswith(".yml")
        and item["path"] != "conference/types.yml"
    ]
    entries: dict[str, dict[str, Any]] = {}

    with httpx.Client(timeout=30.0, follow_redirects=True) as client:
        for path in paths:
            response = client.get(f"{CCFDDL_RAW_BASE}/{path}", headers={"User-Agent": "conference-map-importer/0.1"})
            response.raise_for_status()
            documents = yaml.safe_load(response.text) or []
            for item in documents:
                rank = (item.get("rank") or {}).get("ccf")
                if rank not in {"A", "B"}:
                    continue

                abbreviation = normalize_abbreviation(item["title"])
                cid = conference_id(abbreviation)
                entries[cid] = {
                    "conference_id": cid,
                    "abbreviation": abbreviation,
                    "full_name": item.get("description") or abbreviation,
                    "ccf": rank,
                    "sub": item.get("sub"),
                    "primary_category": SUB_TO_CATEGORY.get(item.get("sub"), "Interdiscipline / Emerging"),
                    "dblp_key": item.get("dblp"),
                    "source_path": path,
                    "source_url": f"{CCFDDL_RAW_BASE}/{path}",
                    "confs": item.get("confs") or [],
                }

    return entries


def parse_deadline(value: str | None) -> str | None:
    if not value or value == "TBD":
        return None
    return value.split(" ", 1)[0]


def deadline_kind(item: dict[str, Any]) -> str:
    comment = (item.get("comment") or "").lower()
    if "abstract" in comment:
        return "abstract"
    if "notification" in comment:
        return "notification"
    if "camera" in comment:
        return "camera_ready"
    return "submission"


def parse_date_range(value: str | None, year: int) -> tuple[str | None, str | None]:
    if not value:
        return None, None
    text = value.replace(",", " ").replace("–", "-").replace("—", "-")
    text = re.sub(r"\s+", " ", text).strip()
    match = re.search(
        r"(?P<m1>[A-Za-z]+)\.?\s+(?P<d1>\d{1,2})(?:\s*-\s*(?:(?P<m2>[A-Za-z]+)\.?\s*)?(?P<d2>\d{1,2}))?",
        text,
    )
    if not match:
        return None, None

    month1 = MONTHS.get(match.group("m1").lower())
    if not month1:
        return None, None
    month2 = MONTHS.get((match.group("m2") or match.group("m1")).lower(), month1)
    day1 = int(match.group("d1"))
    day2 = int(match.group("d2") or match.group("d1"))
    try:
        start = date(year, month1, day1)
        end_year = year + 1 if month2 < month1 else year
        end = date(end_year, month2, day2)
    except ValueError:
        return None, None
    return start.isoformat(), end.isoformat()


def split_place(value: str | None) -> tuple[str | None, str | None, str | None]:
    if not value or value.strip().upper() in {"TBD", "N/A", "ONLINE"}:
        return None, None, None
    parts = [part.strip() for part in value.split(",") if part.strip()]
    if not parts:
        return None, None, None
    city = parts[0]
    country = parts[-1] if len(parts) > 1 else None
    if len(parts) == 2 and parts[1].strip().lower() in {"ca", "pa", "ga"}:
        return city, parts[1].strip(), "United States"
    country = normalize_country(country)
    state = ", ".join(parts[1:-1]) if len(parts) > 2 else None
    return city, state, country


def next_check_for(item_year: int, has_details: bool) -> str:
    today = date.today()
    if item_year <= today.year + 1 or not has_details:
        return (today + timedelta(days=1)).isoformat()
    return (today + timedelta(days=7)).isoformat()


def build_records(
    lookahead_years: int = 8,
    include_placeholders: bool = False,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    kiise = fetch_kiise_rows()
    ccf = fetch_ccfddl_entries()
    ids = sorted(set(kiise) | set(ccf))
    current_year = date.today().year
    horizon_year = current_year + lookahead_years

    conferences: list[dict[str, Any]] = []
    instances: list[dict[str, Any]] = []
    timestamp = now_iso()

    for cid in ids:
        k = kiise.get(cid, {})
        c = ccf.get(cid, {})
        abbreviation = c.get("abbreviation") or k.get("abbreviation") or cid.upper()
        full_name = c.get("full_name") or k.get("full_name") or abbreviation
        primary_category = infer_category(full_name, c.get("sub"))
        ranking = {
            "ccf": c.get("ccf"),
            "kiise": k.get("kiise"),
        }
        source_urls = [SOURCE_CCFDDL, SOURCE_CCFDDL_SITE]
        if c.get("source_url"):
            source_urls.append(c["source_url"])
        if k.get("source_url"):
            source_urls.append(k["source_url"])

        conferences.append(
            {
                "conference_id": cid,
                "abbreviation": abbreviation,
                "full_name": full_name,
                "homepage_root": None,
                "ranking": ranking,
                "primary_category": primary_category,
                "secondary_categories": [],
                "purpose_summary": f"{full_name} tracks research topics in {primary_category}.",
                "known_series_pattern": "annual",
                "typical_months": [],
                "tracking_priority": "high" if ranking.get("ccf") == "A" or ranking.get("kiise") == "최우수" else "medium",
                "source_urls": sorted(set(source_urls)),
                "active": True,
                "created_at": timestamp,
                "updated_at": timestamp,
                "source_metadata": {
                    "dblp_key": c.get("dblp_key") or k.get("dblp_key"),
                    "ccfddl_path": c.get("source_path"),
                    "kiise": k.get("source_metadata"),
                },
            }
        )

        confs_by_year = {int(item["year"]): item for item in c.get("confs", []) if current_year <= int(item["year"]) <= horizon_year}
        years = sorted(confs_by_year)
        if include_placeholders:
            years = list(range(current_year, horizon_year + 1))

        for year in years:
            source_instance = confs_by_year.get(year, {})
            start_date, end_date = parse_date_range(source_instance.get("date"), year)
            timeline_items = source_instance.get("timeline") or []
            timeline = timeline_items[0] if timeline_items else {}
            city, state, country = split_place(source_instance.get("place"))
            has_details = bool(source_instance)
            website_status = "discovered" if source_instance.get("link") else "not_found"
            event_status = "date_confirmed" if start_date else "unknown"
            if source_instance.get("place") and city:
                event_status = "venue_confirmed"

            evidence = []
            deadline_events = []
            if source_instance.get("link"):
                for index, round_item in enumerate(timeline_items):
                    if round_item.get("abstract_deadline"):
                        deadline_events.append(
                            {
                                "deadline_id": str(uuid.uuid5(uuid.NAMESPACE_URL, f"{cid}-{year}-abstract-deadline-{index}")),
                                "instance_id": f"{cid}-{year}",
                                "deadline_type": "abstract",
                                "deadline_date": parse_deadline(round_item.get("abstract_deadline")),
                                "deadline_time_raw": round_item.get("abstract_deadline"),
                                "timezone": source_instance.get("timezone"),
                                "comment": round_item.get("comment"),
                                "source_url": source_instance.get("link"),
                                "confidence": "medium",
                                "evidence": {
                                    "source": "ccfddl",
                                    "raw_timeline": round_item,
                                    "upstream_id": source_instance.get("id"),
                                },
                                "updated_at": timestamp,
                            }
                        )
                    if round_item.get("deadline"):
                        deadline_events.append(
                            {
                                "deadline_id": str(uuid.uuid5(uuid.NAMESPACE_URL, f"{cid}-{year}-deadline-{deadline_kind(round_item)}-{index}")),
                                "instance_id": f"{cid}-{year}",
                                "deadline_type": deadline_kind(round_item),
                                "deadline_date": parse_deadline(round_item.get("deadline")),
                                "deadline_time_raw": round_item.get("deadline"),
                                "timezone": source_instance.get("timezone"),
                                "comment": round_item.get("comment"),
                                "source_url": source_instance.get("link"),
                                "confidence": "medium",
                                "evidence": {
                                    "source": "ccfddl",
                                    "raw_timeline": round_item,
                                    "upstream_id": source_instance.get("id"),
                                },
                                "updated_at": timestamp,
                            }
                        )
                for field, value in {
                    "official_website": source_instance.get("link"),
                    "date": source_instance.get("date"),
                    "place": source_instance.get("place"),
                    "submission_deadline": parse_deadline(timeline.get("deadline")),
                }.items():
                    if value:
                        evidence.append(
                            {
                                "field": field,
                                "value": str(value),
                                "source_url": source_instance.get("link"),
                                "extracted_at": timestamp,
                                "confidence": "medium",
                            }
                        )

            instances.append(
                {
                    "instance_id": f"{cid}-{year}",
                    "conference_id": cid,
                    "year": year,
                    "official_website": source_instance.get("link"),
                    "website_status": website_status,
                    "event_status": event_status,
                    "start_date": start_date,
                    "end_date": end_date,
                    "timezone": source_instance.get("timezone"),
                    "city": city,
                    "state_or_region": state,
                    "country": country,
                    "venue_name": None,
                    "latitude": None,
                    "longitude": None,
                    "coordinate_precision": "unknown",
                    "submission_deadline": parse_deadline(timeline.get("deadline")),
                    "abstract_deadline": parse_deadline(timeline.get("abstract_deadline")),
                    "notification_date": None,
                    "camera_ready_deadline": None,
                    "registration_deadline": None,
                    "last_checked_at": timestamp if has_details else None,
                    "next_check_at": next_check_for(year, has_details),
                    "confidence": "medium" if has_details else "low",
                    "evidence": evidence,
                    "deadline_events": deadline_events,
                    "notes": "Imported from ccfddl; official-site LLM extraction should verify details." if has_details else "Rolling placeholder generated for future tracking.",
                    "updated_at": timestamp,
                }
            )

    return conferences, instances


def infer_category(full_name: str, sub: str | None = None) -> str:
    if sub:
        return SUB_TO_CATEGORY.get(sub, "Interdiscipline / Emerging")

    text = full_name.lower()
    if any(word in text for word in ["vision", "image", "multimedia"]):
        return "Computer Vision"
    if any(word in text for word in ["language", "linguistic", "speech"]):
        return "NLP / Speech / Multimodal AI"
    if any(word in text for word in ["security", "crypt", "privacy"]):
        return "Security / Privacy"
    if any(word in text for word in ["database", "data", "web", "information retrieval"]):
        return "Database / Data Engineering"
    if any(word in text for word in ["architecture", "microarchitecture", "hardware"]):
        return "Computer Architecture"
    return SUB_TO_CATEGORY.get(sub, "AI / Machine Learning")


def import_sources(
    lookahead_years: int = 8,
    include_placeholders: bool = False,
    prune_placeholders: bool = True,
) -> dict[str, int]:
    conferences, instances = build_records(
        lookahead_years=lookahead_years,
        include_placeholders=include_placeholders,
    )
    with connect() as conn:
        ensure_metadata_columns(conn)
        if prune_placeholders:
            conn.execute(
                """
                DELETE FROM instances
                WHERE official_website IS NULL
                  AND confidence = 'low'
                  AND notes = 'Rolling placeholder generated for future tracking.'
                """
            )
        for item in conferences:
            conn.execute(
                """
                INSERT INTO conferences (
                    conference_id, abbreviation, full_name, homepage_root, ranking_json,
                    primary_category, secondary_categories_json, purpose_summary,
                    known_series_pattern, typical_months_json, tracking_priority,
                    source_urls_json, active, created_at, updated_at, source_metadata_json
                )
                VALUES (
                    :conference_id, :abbreviation, :full_name, :homepage_root, :ranking_json,
                    :primary_category, :secondary_categories_json, :purpose_summary,
                    :known_series_pattern, :typical_months_json, :tracking_priority,
                    :source_urls_json, :active, :created_at, :updated_at, :source_metadata_json
                )
                ON CONFLICT(conference_id) DO UPDATE SET
                    abbreviation = excluded.abbreviation,
                    full_name = excluded.full_name,
                    ranking_json = excluded.ranking_json,
                    primary_category = excluded.primary_category,
                    tracking_priority = excluded.tracking_priority,
                    source_urls_json = excluded.source_urls_json,
                    source_metadata_json = excluded.source_metadata_json,
                    updated_at = excluded.updated_at
                """,
                {
                    **item,
                    "ranking_json": dumps(item["ranking"]),
                    "secondary_categories_json": dumps(item["secondary_categories"]),
                    "typical_months_json": dumps(item["typical_months"]),
                    "source_urls_json": dumps(item["source_urls"]),
                    "source_metadata_json": dumps(item["source_metadata"]),
                    "active": 1 if item.get("active", True) else 0,
                },
            )

        for item in instances:
            existing = conn.execute(
                "SELECT confidence, evidence_json FROM instances WHERE instance_id = ?",
                [item["instance_id"]],
            ).fetchone()
            if existing and existing["confidence"] == "high":
                continue
            conn.execute(
                """
                INSERT INTO instances (
                    instance_id, conference_id, year, official_website, website_status,
                    event_status, start_date, end_date, timezone, city, state_or_region,
                    country, venue_name, latitude, longitude, coordinate_precision,
                    submission_deadline, abstract_deadline, notification_date,
                    camera_ready_deadline, registration_deadline, last_checked_at,
                    next_check_at, confidence, evidence_json, notes, updated_at
                )
                VALUES (
                    :instance_id, :conference_id, :year, :official_website, :website_status,
                    :event_status, :start_date, :end_date, :timezone, :city, :state_or_region,
                    :country, :venue_name, :latitude, :longitude, :coordinate_precision,
                    :submission_deadline, :abstract_deadline, :notification_date,
                    :camera_ready_deadline, :registration_deadline, :last_checked_at,
                    :next_check_at, :confidence, :evidence_json, :notes, :updated_at
                )
                ON CONFLICT(instance_id) DO UPDATE SET
                    official_website = COALESCE(excluded.official_website, instances.official_website),
                    website_status = excluded.website_status,
                    event_status = excluded.event_status,
                    start_date = COALESCE(excluded.start_date, instances.start_date),
                    end_date = COALESCE(excluded.end_date, instances.end_date),
                    timezone = COALESCE(excluded.timezone, instances.timezone),
                    city = COALESCE(excluded.city, instances.city),
                    state_or_region = COALESCE(excluded.state_or_region, instances.state_or_region),
                    country = COALESCE(excluded.country, instances.country),
                    submission_deadline = COALESCE(excluded.submission_deadline, instances.submission_deadline),
                    abstract_deadline = COALESCE(excluded.abstract_deadline, instances.abstract_deadline),
                    last_checked_at = COALESCE(excluded.last_checked_at, instances.last_checked_at),
                    next_check_at = excluded.next_check_at,
                    confidence = excluded.confidence,
                    evidence_json = excluded.evidence_json,
                    notes = excluded.notes,
                    updated_at = excluded.updated_at
                """,
                {**item, "evidence_json": dumps(item["evidence"])},
            )

            conn.execute("DELETE FROM deadline_events WHERE instance_id = ?", [item["instance_id"]])
            for deadline in item.get("deadline_events", []):
                conn.execute(
                    """
                    INSERT INTO deadline_events (
                        deadline_id, instance_id, deadline_type, deadline_date,
                        deadline_time_raw, timezone, comment, source_url, confidence,
                        evidence_json, updated_at
                    )
                    VALUES (
                        :deadline_id, :instance_id, :deadline_type, :deadline_date,
                        :deadline_time_raw, :timezone, :comment, :source_url, :confidence,
                        :evidence_json, :updated_at
                    )
                    """,
                    {**deadline, "evidence_json": dumps(deadline["evidence"])},
                )

            if item["evidence"]:
                conn.execute(
                    """
                    INSERT OR IGNORE INTO update_history (
                        history_id, instance_id, field, old_value, new_value, source_url,
                        updated_at, update_method, confidence
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    [
                        str(uuid.uuid5(uuid.NAMESPACE_URL, item["instance_id"] + item["updated_at"])),
                        item["instance_id"],
                        "import",
                        None,
                        "ccfddl-import",
                        SOURCE_CCFDDL,
                        item["updated_at"],
                        "source_importer",
                        item["confidence"],
                    ],
                )

    return {"conferences": len(conferences), "instances": len(instances)}


def ensure_metadata_columns(conn) -> None:
    columns = {row["name"] for row in conn.execute("PRAGMA table_info(conferences)").fetchall()}
    if "source_metadata_json" not in columns:
        conn.execute("ALTER TABLE conferences ADD COLUMN source_metadata_json TEXT NOT NULL DEFAULT '{}'")
    conn.execute(
        """
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
        )
        """
    )
