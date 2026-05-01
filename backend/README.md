# Orbital Conjunctions — Backend

Production-quality Python backend for the Orbital Conjunctions Dashboard.

## Stack

- Python 3.12+
- FastAPI + Uvicorn
- Pydantic v2 / pydantic-settings
- SQLAlchemy 2.x async + Alembic (PostgreSQL via asyncpg, SQLite via aiosqlite for dev/tests)
- `sgp4` for orbit propagation
- `httpx` async for outbound HTTP (CelesTrak)
- APScheduler for periodic TLE refresh and conjunction recompute
- `structlog` for structured logging
- Tooling: `ruff`, `mypy --strict`, `pytest` + `pytest-asyncio`

## Quick start

### 1. Install

```bash
python -m venv .venv
source .venv/bin/activate                      # on Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

### 2. Configure

All settings are read from environment variables (prefix `OC_`) or a `.env` file.
The most useful ones:

| Variable | Default | Description |
| --- | --- | --- |
| `OC_DATABASE_URL` | `sqlite+aiosqlite:///./orbital_conjunctions.db` | Async SQLAlchemy URL |
| `OC_CELESTRAK_URL` | active satellites endpoint | TLE source |
| `OC_SCREENING_HORIZON_HOURS` | `72` | Conjunction look-ahead |
| `OC_TLE_REFRESH_INTERVAL_HOURS` | `4` | TLE refresh cadence |
| `OC_CONJUNCTION_REFRESH_INTERVAL_MINUTES` | `30` | Recompute cadence |
| `OC_ENABLE_SCHEDULER` | `false` | Enable APScheduler in the FastAPI lifespan |

### 3. Migrate

```bash
alembic upgrade head
```

### 4. Run

```bash
uvicorn oc.main:app --reload
```

The API is then served at `http://localhost:8000/api`. Interactive docs are
available at `/docs` and `/redoc`.

## Running tests

```bash
pytest -q                  # all tests, in-memory SQLite
ruff check src tests       # lint
ruff format --check src tests
mypy src                   # strict type-checking
```

## Layout

```
backend/
├── pyproject.toml
├── Dockerfile               # python:3.12-slim, multi-stage
├── alembic.ini
├── alembic/                 # migrations
├── src/oc/
│   ├── main.py              # FastAPI app factory
│   ├── config.py            # pydantic-settings
│   ├── db.py                # async engine + session
│   ├── models.py            # SQLAlchemy ORM
│   ├── schemas.py           # Pydantic v2 contracts
│   ├── api/                 # HTTP routers (health/stats/satellites/conjunctions)
│   ├── services/            # tle_fetcher / propagation / conjunctions
│   └── workers/scheduler.py # APScheduler jobs
└── tests/                   # pytest, pytest-asyncio, in-memory SQLite
```

## Conjunction screening pipeline

Three-tier filter:

1. **Perigee/apogee** — discard pairs whose altitude bands cannot intersect.
2. **Coarse temporal sweep** — propagate at 60 s steps, keep windows < 50 km.
3. **Refinement** — fine sweep + bounded `scipy.optimize.minimize_scalar` to
   recover sub-second TCAs.

The probability column is a placeholder Gaussian on the miss distance:
`exp(-miss_km^2 / (2 * sigma^2))` with `sigma = 1 km`. **It is not an
operational probability of collision.** Treat it as a triage indicator only.

## Endpoints

See [`docs/api-contract.md`](../docs/api-contract.md) for the canonical
specification. Implemented routes:

- `GET /api/health`
- `GET /api/stats`
- `GET /api/satellites?q=&limit=&offset=`
- `GET /api/conjunctions?max_distance_km=&hours=&limit=&offset=`
- `GET /api/conjunctions/{id}`
