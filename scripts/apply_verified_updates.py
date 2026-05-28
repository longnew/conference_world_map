from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import sys
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.app.countries import normalize_country
from backend.app.db import connect, dumps, loads


VERIFIED = [
    {
        "instance_id": "popl-2026",
        "fields": {
            "start_date": "2026-01-11",
            "end_date": "2026-01-17",
            "city": "Rennes",
            "country": "France",
            "venue_name": "le Couvent des Jacobins",
            "submission_deadline": "2025-07-10",
            "notification_date": "2025-11-06",
            "camera_ready_deadline": "2025-12-01",
        },
        "deadlines": [
            ("submission", "2025-07-10", "2025-07-10 23:59 AoE", "research papers"),
            ("notification", "2025-11-06", "2025-11-06", "research papers"),
            ("camera_ready", "2025-12-01", "2025-12-01", "research papers"),
        ],
        "source_urls": ["https://popl26.sigplan.org/", "https://conf.researchr.org/track/POPL-2026/POPL-2026-popl-research-papers"],
        "notes": "Official CFP states there is no abstract deadline.",
    },
    {
        "instance_id": "soda-2026",
        "fields": {
            "start_date": "2026-01-11",
            "end_date": "2026-01-14",
            "city": "Vancouver",
            "country": "Canada",
            "venue_name": "Hyatt Regency Vancouver",
            "submission_deadline": "2025-07-14",
        },
        "deadlines": [
            ("submission", "2025-07-14", "2025-07-14 23:59 AoE", "paper submission"),
            ("notification", None, "October 2025", "acceptance notification"),
        ],
        "source_urls": ["https://www.siam.org/conferences-events/past-event-archive/soda26/", "https://www.siam.org/conferences-events/past-event-archive/soda26/submissions/"],
        "notes": "Official SIAM page redirects to past-event archive; notification is month-level only.",
    },
    {
        "instance_id": "vmcai-2026",
        "fields": {
            "start_date": "2026-01-12",
            "end_date": "2026-01-13",
            "city": "Rennes",
            "country": "France",
            "venue_name": "le Couvent des Jacobins",
            "submission_deadline": "2025-09-15",
            "notification_date": "2025-11-06",
            "camera_ready_deadline": "2025-11-20",
        },
        "deadlines": [
            ("submission", "2025-09-15", "2025-09-15", "extended paper submission"),
            ("notification", "2025-11-06", "2025-11-06", "notification"),
            ("camera_ready", "2025-11-20", "2025-11-20", "camera-ready"),
        ],
        "source_urls": ["https://conf.researchr.org/home/VMCAI-2026"],
        "notes": "No abstract deadline directly stated.",
    },
    {
        "instance_id": "cidr-2026",
        "fields": {
            "start_date": "2026-01-18",
            "end_date": "2026-01-21",
            "city": "Santa Cruz",
            "country": "United States",
            "venue_name": "Chaminade Resort & Spa",
            "submission_deadline": "2025-08-05",
            "notification_date": "2025-10-06",
            "camera_ready_deadline": "2025-12-01",
        },
        "deadlines": [
            ("submission", "2025-08-05", "2025-08-05", "paper submission"),
            ("notification", "2025-10-06", "2025-10-06", "notification"),
            ("camera_ready", "2025-12-01", "2025-12-01", "camera-ready"),
        ],
        "source_urls": ["https://www.cidrdb.org/cidr2026/", "https://www.cidrdb.org/cidr2026/cfp.html", "https://www.cidrdb.org/cidr2026/registration.html"],
        "notes": "No separate abstract deadline directly stated.",
    },
    {
        "instance_id": "aaai-2026",
        "fields": {
            "start_date": "2026-01-20",
            "end_date": "2026-01-27",
            "city": "Singapore",
            "country": "Singapore",
            "venue_name": "Singapore EXPO",
            "abstract_deadline": "2025-07-25",
            "submission_deadline": "2025-08-01",
            "notification_date": "2025-11-08",
            "camera_ready_deadline": "2025-11-16",
        },
        "deadlines": [
            ("abstract", "2025-07-25", "2025-07-25 23:59 UTC-12", "abstract deadline"),
            ("submission", "2025-08-01", "2025-08-01 23:59 UTC-12", "full paper deadline"),
            ("notification", "2025-11-08", "2025-11-08", "notification"),
            ("camera_ready", "2025-11-16", "2025-11-16", "camera-ready"),
        ],
        "source_urls": ["https://aaai.org/conference/aaai/aaai-26/"],
        "notes": "Camera-ready date uses the current corrected date.",
    },
    {
        "instance_id": "ieee-acm-cgo-2026",
        "fields": {
            "start_date": "2026-01-31",
            "end_date": "2026-02-04",
            "city": "Sydney",
            "country": "Australia",
            "venue_name": "International Convention Centre Sydney",
            "submission_deadline": "2025-09-11",
            "notification_date": "2025-11-03",
        },
        "deadlines": [
            ("submission", "2025-05-29", "2025-05-29", "round 1"),
            ("notification", "2025-07-21", "2025-07-21", "round 1"),
            ("submission", "2025-09-11", "2025-09-11", "round 2"),
            ("notification", "2025-11-03", "2025-11-03", "round 2"),
        ],
        "source_urls": ["https://conf.researchr.org/home/cgo-2026", "https://2026.cgo.org/track/cgo-2026-papers", "https://2026.cgo.org/venue/hpcc-2026-venue"],
        "notes": "Two submission rounds are directly stated.",
    },
    {
        "instance_id": "ppopp-2026",
        "fields": {
            "start_date": "2026-01-31",
            "end_date": "2026-02-04",
            "city": "Sydney",
            "country": "Australia",
            "venue_name": "International Convention Centre Sydney",
            "submission_deadline": "2025-09-01",
            "notification_date": "2025-11-10",
        },
        "deadlines": [
            ("submission", "2025-09-01", "2025-09-01", "papers"),
            ("notification", "2025-11-10", "2025-11-10", "papers"),
        ],
        "source_urls": ["https://ppopp26.sigplan.org/", "https://ppopp26.sigplan.org/venue/hpcc-2026-venue", "https://ppopp26.sigplan.org/track/PPoPP-2026-papers"],
        "notes": "No separate abstract deadline directly stated.",
    },
    {
        "instance_id": "wsdm-2026",
        "fields": {
            "start_date": "2026-02-22",
            "end_date": "2026-02-26",
            "city": "Boise",
            "country": "United States",
            "venue_name": "Boise Centre",
            "abstract_deadline": "2025-08-07",
            "submission_deadline": "2025-08-14",
            "notification_date": "2025-10-23",
            "camera_ready_deadline": "2025-12-17",
        },
        "deadlines": [
            ("abstract", "2025-08-07", "2025-08-07", "papers"),
            ("submission", "2025-08-14", "2025-08-14", "papers"),
            ("notification", "2025-10-23", "2025-10-23", "papers"),
            ("camera_ready", "2025-12-17", "2025-12-17", "camera-ready year inferred from WSDM 2026 context"),
        ],
        "source_urls": ["https://wsdm-conference.org/2026/index.php/call-for-papers/", "https://wsdm-conference.org/2026/index.php/venue-and-travel-information/", "https://wsdm-conference.org/2026/index.php/camera-ready-instructions/"],
        "notes": "Camera-ready page states December 17th in WSDM 2026 context.",
    },
    {
        "instance_id": "ndss-2026",
        "fields": {
            "start_date": "2026-02-23",
            "end_date": "2026-02-27",
            "city": "San Diego",
            "country": "United States",
            "venue_name": "Wyndham San Diego Bayside",
            "submission_deadline": "2025-08-06",
            "notification_date": "2025-10-22",
            "camera_ready_deadline": "2025-12-17",
        },
        "deadlines": [
            ("submission", "2025-04-23", "2025-04-23", "summer cycle"),
            ("notification", "2025-07-02", "2025-07-02", "summer cycle"),
            ("notification", "2025-08-13", "2025-08-13", "summer major revision"),
            ("camera_ready", "2025-09-10", "2025-09-10", "summer cycle"),
            ("submission", "2025-08-06", "2025-08-06", "fall cycle"),
            ("notification", "2025-10-22", "2025-10-22", "fall cycle"),
            ("notification", "2025-12-03", "2025-12-03", "fall major revision"),
            ("camera_ready", "2025-12-17", "2025-12-17", "fall cycle"),
        ],
        "source_urls": ["https://www.ndss-symposium.org/ndss2026/", "https://www.ndss-symposium.org/ndss2026/submissions/call-for-papers/", "https://www.ndss-symposium.org/ndss2026/attend/registration-information/"],
        "notes": "Official CFP has two review cycles.",
    },
]


def main() -> None:
    timestamp = datetime.now(timezone.utc).isoformat()
    updated = 0
    with connect() as conn:
        for item in VERIFIED:
            existing = conn.execute("SELECT * FROM instances WHERE instance_id = ?", [item["instance_id"]]).fetchone()
            if not existing:
                continue
            fields = {key: normalize_country(value) if key == "country" else value for key, value in item["fields"].items()}
            evidence = loads(existing["evidence_json"], [])
            evidence.append(
                {
                    "field": "codex_subagent_official_verification",
                    "value": item["notes"],
                    "source_url": item["source_urls"][0],
                    "source_urls": item["source_urls"],
                    "extracted_at": timestamp,
                    "confidence": "high",
                }
            )
            assignments = [f"{field} = ?" for field in fields]
            values = list(fields.values())
            values.extend(["high", dumps(evidence), item["notes"], timestamp, item["instance_id"]])
            conn.execute(
                f"""
                UPDATE instances
                SET {', '.join(assignments)}, confidence = ?, evidence_json = ?, notes = ?, updated_at = ?
                WHERE instance_id = ?
                """,
                values,
            )
            conn.execute("DELETE FROM deadline_events WHERE instance_id = ? AND confidence != 'high'", [item["instance_id"]])
            for index, (kind, date_value, raw_value, comment) in enumerate(item["deadlines"]):
                conn.execute(
                    """
                    INSERT OR REPLACE INTO deadline_events (
                        deadline_id, instance_id, deadline_type, deadline_date,
                        deadline_time_raw, timezone, comment, source_url, confidence,
                        evidence_json, updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    [
                        str(uuid.uuid5(uuid.NAMESPACE_URL, f"{item['instance_id']}:{kind}:{index}:{raw_value}")),
                        item["instance_id"],
                        kind,
                        date_value,
                        raw_value,
                        None,
                        comment,
                        item["source_urls"][0],
                        "high",
                        dumps({"source_urls": item["source_urls"], "notes": item["notes"]}),
                        timestamp,
                    ],
                )
            for field, new_value in fields.items():
                old_value = existing[field]
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
                        str(uuid.uuid5(uuid.NAMESPACE_URL, f"{item['instance_id']}:{field}:{new_value}:{timestamp}")),
                        item["instance_id"],
                        field,
                        old_value,
                        new_value,
                        item["source_urls"][0],
                        timestamp,
                        "codex_subagent_official_verification",
                        "high",
                    ],
                )
            updated += 1
    print(f"Applied verified updates to {updated} instances.")


if __name__ == "__main__":
    main()
