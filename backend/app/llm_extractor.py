from __future__ import annotations

import json
import os
import re
import uuid
from datetime import datetime, timezone
from typing import Any

import httpx
from bs4 import BeautifulSoup

from .countries import normalize_country
from .db import connect, dumps, loads

OPENAI_RESPONSES_URL = "https://api.openai.com/v1/responses"
DEFAULT_MODEL = "gpt-4o-mini"

EXTRACTION_SCHEMA = {
    "type": "object",
    "properties": {
        "is_official_current_year_page": {"type": "boolean"},
        "start_date": {"type": "string"},
        "end_date": {"type": "string"},
        "city": {"type": "string"},
        "country": {"type": "string"},
        "venue_name": {"type": "string"},
        "abstract_deadline": {"type": "string"},
        "submission_deadline": {"type": "string"},
        "notification_date": {"type": "string"},
        "camera_ready_deadline": {"type": "string"},
        "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
        "evidence_summary": {"type": "string"},
    },
    "required": [
        "is_official_current_year_page",
        "start_date",
        "end_date",
        "city",
        "country",
        "venue_name",
        "abstract_deadline",
        "submission_deadline",
        "notification_date",
        "camera_ready_deadline",
        "confidence",
        "evidence_summary",
    ],
    "additionalProperties": False,
}


def empty_to_none(value: str | None) -> str | None:
    if not value:
        return None
    value = value.strip()
    if value.lower() in {"", "unknown", "not found", "null", "none", "tbd", "n/a"}:
        return None
    return value


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def fetch_page_text(url: str) -> str:
    response = httpx.get(
        url,
        timeout=30.0,
        follow_redirects=True,
        headers={"User-Agent": "conference-map-llm-worker/0.1"},
    )
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    for tag in soup(["script", "style", "noscript", "svg"]):
        tag.decompose()
    text = soup.get_text("\n")
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    return text.strip()[:24000]


def call_openai_extractor(
    *,
    api_key: str,
    model: str,
    instance: dict[str, Any],
    page_text: str,
) -> dict[str, Any]:
    prompt = f"""
Extract conference event details from the official page text.

Rules:
- Return JSON only through the schema.
- Use YYYY-MM-DD for date fields when explicitly present.
- If a field is not explicitly present, return an empty string.
- Do not infer a venue from a city.
- Do not use past-year information as current-year information.
- Mark confidence high only when the page text directly states the value.

Instance:
- id: {instance['instance_id']}
- abbreviation: {instance['abbreviation']}
- expected year: {instance['year']}
- official website: {instance['official_website']}

Page text:
{page_text}
""".strip()

    payload = {
        "model": model,
        "input": [
            {
                "role": "system",
                "content": "You extract conference dates, venue, city, country, and deadlines with strict provenance discipline.",
            },
            {"role": "user", "content": prompt},
        ],
        "text": {
            "format": {
                "type": "json_schema",
                "name": "conference_event_extraction",
                "strict": True,
                "schema": EXTRACTION_SCHEMA,
            }
        },
    }
    response = httpx.post(
        OPENAI_RESPONSES_URL,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json=payload,
        timeout=90.0,
    )
    response.raise_for_status()
    data = response.json()
    for output in data.get("output", []):
        for content in output.get("content", []):
            if content.get("type") == "output_text":
                return json.loads(content["text"])
    raise RuntimeError("No structured output_text returned by OpenAI")


def candidate_instances(limit: int) -> list[dict[str, Any]]:
    with connect() as conn:
        return [
            dict(row)
            for row in conn.execute(
                """
                SELECT i.*, c.abbreviation, c.full_name
                FROM instances i
                JOIN conferences c ON c.conference_id = i.conference_id
                WHERE i.official_website IS NOT NULL
                  AND i.confidence != 'high'
                ORDER BY i.start_date IS NULL, i.start_date, i.instance_id
                LIMIT ?
                """,
                [limit],
            ).fetchall()
        ]


def apply_extraction(instance: dict[str, Any], extraction: dict[str, Any], source_url: str) -> bool:
    if not extraction.get("is_official_current_year_page"):
        return False
    if extraction.get("confidence") != "high":
        return False

    fields = {
        "start_date": empty_to_none(extraction.get("start_date")),
        "end_date": empty_to_none(extraction.get("end_date")),
        "city": empty_to_none(extraction.get("city")),
        "country": normalize_country(empty_to_none(extraction.get("country"))),
        "venue_name": empty_to_none(extraction.get("venue_name")),
        "abstract_deadline": empty_to_none(extraction.get("abstract_deadline")),
        "submission_deadline": empty_to_none(extraction.get("submission_deadline")),
        "notification_date": empty_to_none(extraction.get("notification_date")),
        "camera_ready_deadline": empty_to_none(extraction.get("camera_ready_deadline")),
    }
    fields = {key: value for key, value in fields.items() if value}
    if not fields:
        return False

    timestamp = utc_now()
    evidence = loads(instance.get("evidence_json"), [])
    evidence.append(
        {
            "field": "llm_official_page_extraction",
            "value": extraction.get("evidence_summary", ""),
            "source_url": source_url,
            "extracted_at": timestamp,
            "confidence": "high",
        }
    )

    with connect() as conn:
        assignments = [f"{field} = ?" for field in fields]
        values = list(fields.values())
        values.extend(["high", dumps(evidence), timestamp, instance["instance_id"]])
        conn.execute(
            f"""
            UPDATE instances
            SET {', '.join(assignments)}, confidence = ?, evidence_json = ?, updated_at = ?
            WHERE instance_id = ?
            """,
            values,
        )
        for field, new_value in fields.items():
            old_value = instance.get(field)
            if old_value == new_value:
                continue
            conn.execute(
                """
                INSERT INTO update_history (
                    history_id, instance_id, field, old_value, new_value, source_url,
                    updated_at, update_method, confidence
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    str(uuid.uuid5(uuid.NAMESPACE_URL, f"{instance['instance_id']}:{field}:{new_value}:{timestamp}")),
                    instance["instance_id"],
                    field,
                    old_value,
                    new_value,
                    source_url,
                    timestamp,
                    "llm_official_page_extraction",
                    "high",
                ],
            )
    return True


def run_llm_extraction(limit: int = 5, model: str | None = None) -> dict[str, int]:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return {"processed": 0, "updated": 0, "skipped": 0, "failed": 0, "missing_api_key": 1}

    selected_model = model or os.getenv("OPENAI_MODEL", DEFAULT_MODEL)
    processed = updated = skipped = failed = 0
    for instance in candidate_instances(limit):
        processed += 1
        try:
            page_text = fetch_page_text(instance["official_website"])
            extraction = call_openai_extractor(
                api_key=api_key,
                model=selected_model,
                instance=instance,
                page_text=page_text,
            )
            if apply_extraction(instance, extraction, instance["official_website"]):
                updated += 1
            else:
                skipped += 1
        except Exception:
            failed += 1
    return {"processed": processed, "updated": updated, "skipped": skipped, "failed": failed, "missing_api_key": 0}
