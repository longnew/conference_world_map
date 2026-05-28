from __future__ import annotations

import os
import time
from datetime import date, datetime, timedelta, timezone
from collections import defaultdict, deque
from typing import Optional

from fastapi import FastAPI, Header, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware

from .countries import country_ko, normalize_country
from .db import init_db, loads, rows, row

app = FastAPI(title="AI/CS Conference Tracker")

RATE_LIMIT_PER_MINUTE = int(os.getenv("RATE_LIMIT_PER_MINUTE", "120"))
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN")
request_log: dict[str, deque[float]] = defaultdict(deque)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def rate_limit(request: Request, call_next):
    if RATE_LIMIT_PER_MINUTE <= 0:
        return await call_next(request)

    forwarded_for = request.headers.get("x-forwarded-for", "")
    client_ip = forwarded_for.split(",", 1)[0].strip() if forwarded_for else ""
    client_ip = client_ip or (request.client.host if request.client else "unknown")
    now = time.time()
    bucket = request_log[client_ip]

    while bucket and now - bucket[0] > 60:
        bucket.popleft()

    if len(bucket) >= RATE_LIMIT_PER_MINUTE:
        raise HTTPException(status_code=429, detail="Rate limit exceeded")

    bucket.append(now)
    return await call_next(request)


@app.on_event("startup")
def startup() -> None:
    init_db()


def require_admin_token(authorization: Optional[str]) -> None:
    if not ADMIN_TOKEN:
        return
    expected = f"Bearer {ADMIN_TOKEN}"
    if authorization != expected:
        raise HTTPException(status_code=401, detail="Admin token required")


def normalize_conference(item: dict) -> dict:
    return {
        **item,
        "ranking": loads(item.pop("ranking_json"), {}),
        "secondary_categories": loads(item.pop("secondary_categories_json"), []),
        "typical_months": loads(item.pop("typical_months_json"), []),
        "source_urls": loads(item.pop("source_urls_json"), []),
        "active": bool(item["active"]),
    }


def normalize_instance(item: dict) -> dict:
    item["country"] = normalize_country(item.get("country"))
    item["country_ko"] = country_ko(item.get("country"))
    return {
        **item,
        "ranking": loads(item.pop("ranking_json"), {}),
        "secondary_categories": loads(item.pop("secondary_categories_json"), []),
        "source_urls": loads(item.pop("source_urls_json"), []),
        "evidence": loads(item.pop("evidence_json"), []),
    }


def instance_select() -> str:
    return """
        SELECT i.*, c.abbreviation, c.full_name, c.homepage_root,
               c.ranking_json, c.primary_category, c.secondary_categories_json,
               c.purpose_summary, c.tracking_priority, c.source_urls_json
        FROM instances i
        JOIN conferences c ON c.conference_id = i.conference_id
    """


@app.get("/api/health")
def health():
    return {"ok": True, "date": date.today().isoformat()}


@app.get("/api/stats")
def stats():
    conferences = conferences_data = rows("SELECT ranking_json FROM conferences WHERE active = 1")
    instances_data = rows("SELECT latitude, longitude, end_date FROM instances")
    deadlines_data = rows("SELECT deadline_date FROM deadline_events")
    today = date.today().isoformat()
    ccf_ab = 0
    kiise = 0
    for item in conferences_data:
        ranking = loads(item["ranking_json"], {})
        if ranking.get("ccf") in {"A", "B"}:
            ccf_ab += 1
        if ranking.get("kiise"):
            kiise += 1
    future_instances = [
        item for item in instances_data if item["end_date"] is None or item["end_date"] >= today
    ]
    return {
        "conferences": len(conferences),
        "instances": len(instances_data),
        "future_instances": len(future_instances),
        "ccf_ab_conferences": ccf_ab,
        "kiise_ranked_conferences": kiise,
        "map_ready_future": sum(1 for item in future_instances if item["latitude"] is not None and item["longitude"] is not None),
        "future_deadlines": sum(1 for item in deadlines_data if item["deadline_date"] is None or item["deadline_date"] >= today),
    }


@app.get("/api/conferences")
def conferences():
    data = rows("SELECT * FROM conferences WHERE active = 1 ORDER BY abbreviation")
    return [normalize_conference(item) for item in data]


@app.get("/api/instances")
def instances(
    future_only: bool = False,
    status: Optional[str] = None,
    year: Optional[int] = None,
    confidence: Optional[str] = None,
):
    filters: list[str] = ["1 = 1"]
    params: list[object] = []
    today = date.today().isoformat()

    if future_only:
        filters.append("(i.end_date IS NULL OR i.end_date >= ?)")
        params.append(today)
    if status == "venue_confirmed":
        filters.append("i.event_status = 'venue_confirmed'")
    elif status == "tracking":
        filters.append("(i.venue_name IS NULL OR i.latitude IS NULL OR i.longitude IS NULL)")
    elif status:
        filters.append("i.event_status = ?")
        params.append(status)
    if year:
        filters.append("i.year = ?")
        params.append(year)
    if confidence:
        filters.append("i.confidence = ?")
        params.append(confidence)

    data = rows(
        f"{instance_select()} WHERE {' AND '.join(filters)} ORDER BY i.year, c.abbreviation",
        params,
    )
    return [normalize_instance(item) for item in data]


@app.get("/api/updates/recent")
def recent_updates(days: int = Query(30, ge=1, le=365)):
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    data = rows(
        f"{instance_select()} WHERE i.updated_at >= ? ORDER BY i.updated_at DESC",
        [cutoff],
    )
    return [normalize_instance(item) for item in data]


@app.get("/api/conflicts")
def conflicts():
    data = rows("SELECT * FROM conflicts ORDER BY created_at DESC")
    for item in data:
        item["values"] = loads(item.pop("values_json"), [])
    return data


@app.get("/api/deadlines")
def deadlines(future_only: bool = True):
    filters = ["1 = 1"]
    params: list[object] = []
    if future_only:
        filters.append("(d.deadline_date IS NULL OR d.deadline_date >= ?)")
        params.append(date.today().isoformat())
    data = rows(
        f"""
        SELECT d.*, i.year, c.abbreviation, c.full_name, c.primary_category, c.ranking_json
        FROM deadline_events d
        JOIN instances i ON i.instance_id = d.instance_id
        JOIN conferences c ON c.conference_id = i.conference_id
        WHERE {' AND '.join(filters)}
        ORDER BY d.deadline_date IS NULL, d.deadline_date, c.abbreviation
        """,
        params,
    )
    for item in data:
        item["ranking"] = loads(item.pop("ranking_json"), {})
        item["evidence"] = loads(item.pop("evidence_json"), {})
    return data


@app.post("/api/admin/refresh/{instance_id}")
def refresh_instance(instance_id: str, authorization: Optional[str] = Header(default=None)):
    require_admin_token(authorization)
    found = row("SELECT * FROM instances WHERE instance_id = ?", [instance_id])
    if not found:
        raise HTTPException(status_code=404, detail="Instance not found")
    return {
        "instance_id": instance_id,
        "status": "queued",
        "note": "Crawler worker is stubbed in this milestone; no result fields were changed.",
    }


@app.post("/api/admin/refresh-all")
def refresh_all(authorization: Optional[str] = Header(default=None)):
    require_admin_token(authorization)
    return {
        "status": "queued",
        "note": "Scheduler/crawler hooks are present as API contracts; implementation is the next milestone.",
    }
