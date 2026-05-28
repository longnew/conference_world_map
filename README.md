# AI/CS Conference Tracker

미래 AI/Computer Science 국제 학회의 venue, 일정, deadline을 추적하는 지도형 웹 애플리케이션입니다.

현재 상태는 첫 번째 실행 가능한 마일스톤입니다. 데이터베이스, API, React UI, 지도 화면, tracking/deadline/recent 탭 구조가 준비되어 있고, crawler와 scheduler는 다음 마일스톤에서 채울 수 있도록 명시적인 stub으로 남겨두었습니다.

## Stack

- Backend: FastAPI + SQLite
- Frontend: React + Vite + Leaflet
- Database: `data/conference_map.sqlite3`
- Seed data: `data/seed_data.json`

## Map Data

The frontend does not use a third-party map tile server. It renders a bundled
Natural Earth 1:110m country boundary GeoJSON from:

https://github.com/nvkelso/natural-earth-vector

Natural Earth raster and vector map data is public domain. The bundled file is a
reduced copy that keeps only country names and geometry for app rendering.

## Run

Backend:

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r backend\requirements.txt
.\.venv\Scripts\python -m uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
```

Frontend:

```powershell
cd frontend
npm install
npm run dev
```

Open:

```text
http://127.0.0.1:5173
```

## Public Access And Abuse Protection

Do not expose the Vite dev server or Uvicorn directly to the public internet.

Recommended production shape:

- Build the frontend with `npm run build`.
- Serve `frontend/dist` behind a reverse proxy or static host.
- Run FastAPI behind a reverse proxy.
- Put Cloudflare, another CDN/WAF, or a managed host in front of the origin.
- Set `ADMIN_TOKEN` before exposing admin endpoints.
- Keep `RATE_LIMIT_PER_MINUTE` enabled as an app-level backstop.

The built-in rate limiter reduces simple abuse against the API, but it cannot stop volumetric DDoS traffic by itself. Real DDoS protection must happen upstream, before traffic reaches this machine.

## API

- `GET /api/health`
- `GET /api/conferences`
- `GET /api/instances`
- `GET /api/instances?future_only=true`
- `GET /api/instances?status=venue_confirmed`
- `GET /api/instances?status=tracking`
- `GET /api/updates/recent`
- `GET /api/conflicts`
- `POST /api/admin/refresh/{instance_id}`
- `POST /api/admin/refresh-all`

## Data Policy

Seed data intentionally avoids guessed event dates and venues. If an official current-year site, venue, deadline, or coordinate has not been extracted and stored with evidence, the field remains `null` and appears as tracking/TBD in the UI.

Ranking and deadline seed sources used by the importer:

- KIISE/BK/SNU/POSTECH/DBLP CSV: https://gist.github.com/Pusnow/6eb933355b5cb8d31ef1abcb3c3e1206
- CCFDDL source repository: https://github.com/ccfddl/ccf-deadlines
- CCFDDL public site: https://ccfddl.com/

Import the full seed registry and rolling future instances:
Import the full seed registry and source-backed yearly instances:

```powershell
.\.venv\Scripts\python scripts\import_sources.py --lookahead-years 1
```

By default, the importer only creates yearly instances that already appear in an upstream source such as CCFDDL or later official-site extraction. It does not create empty `{conference} x {year}` placeholders. The default lookahead is fixed to 1 year.

Empty placeholders are available only for deliberate debugging/prototyping with:

```powershell
.\.venv\Scripts\python scripts\import_sources.py --lookahead-years 1 --include-placeholders
```

Refresh cadence:

- Ranking/source import: monthly
- Yearly official-site discovery: daily for unknown/high-priority instances
- Date, venue, and submission extraction: daily for events within 6 months or with missing venue/date; weekly otherwise
- Geocoding: whenever city or venue changes
- Archive pass: daily
- LLM official-page extraction: daily, default 5 candidate instances per run when `OPENAI_API_KEY` is set

Future LLM-assisted extraction should run as worker jobs. Workers must store raw source URLs, extracted fields, confidence, and conflicts instead of silently overwriting existing official evidence.

Run the LLM official-page worker manually:

```powershell
$env:OPENAI_API_KEY = "..."
.\.venv\Scripts\python scripts\run_llm_extraction.py --limit 5
```

## Next Milestones

1. Implement official website discovery with candidate URL storage.
2. Add source-specific extraction for Important Dates, Venue, CFP, and Program pages.
3. Add Nominatim geocoding with coordinate precision metadata.
4. Persist update history and conflict records for changed fields.
5. Add admin edit/resolve screens.
