# NYC Subway Live ETA

A production-leaning FastAPI backend that fuses **MTA GTFS-Realtime** feeds with static **GTFS** schedules to compute:
- Live arrivals per station/direction
- Transfer‑aware, delay‑aware route ETAs
- Re-routing when Alerts indicate disruptions

## Quick start

### Local (Python 3.11+)
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # set values
uvicorn app.main:app --reload
```

### Docker (with Redis for caching and background workers)
```bash
docker compose up --build
# API at http://localhost:8000, Redis at localhost:6379
```

### Run tests
```bash
pytest -q
```

## Environment
Copy `.env.example` to `.env` and set:
- `MTA_FEED_URLS`: comma-separated GTFS-RT feed URLs (e.g., nqrw, ace, bdfm…)
- `GTFS_STATIC_PATH`: path to unpacked GTFS static zip (stops.txt, routes.txt, stop_times.txt, transfers.txt, trips.txt…)
- `REDIS_URL`: e.g., `redis://redis:6379/0` (Docker) or `redis://localhost:6379/0` (local)
- `POLL_SECONDS`: how often the poller fetches GTFS-RT (default 30)

## API
- `GET /health` → service status
- `GET /arrivals?stop_id=R23N&limit=3` → next arrivals for a stop+direction
- `GET /route?from=R23N&to=A12S&at=now` → fastest path & ETA using live headways (stubbed initially)

OpenAPI docs at `/docs`.

## Dev notes
- **app/ingest**: decodes GTFS‑RT protobuf, merges with static data, writes compact state into Redis.
- **app/graph**: builds a station graph from GTFS static; supports Dijkstra/A* with transfer penalties.
- **app/service**: HTTP handlers and response schemas.
- **tests/**: unit + integration tests (mocks for GTFS‑RT).

This is an MVP scaffold—safe to push commits daily as you flesh out each module.
