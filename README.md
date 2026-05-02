# Orbital Collision Risk Dashboard

[![CI](https://github.com/tanguychenier/Orbital-Collision-Risk-Dashboard/actions/workflows/ci.yml/badge.svg)](https://github.com/tanguychenier/Orbital-Collision-Risk-Dashboard/actions/workflows/ci.yml) [![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE) [![Python 3.12+](https://img.shields.io/badge/Python-3.12+-3776AB.svg)](https://www.python.org/) [![Vue 3](https://img.shields.io/badge/Vue-3-4FC08D.svg)](https://vuejs.org/) [![Docker](https://img.shields.io/badge/Docker-required-2496ED.svg)](https://www.docker.com/)

> A free, open-source dashboard that screens **publicly available TLE data** for upcoming **satellite-to-satellite close approaches** and shows them on a 3D globe. Useful for operators wanting a sanity check, researchers, journalists, and anyone interested in the growing congestion of low Earth orbit.

> **Disclaimer:** this is a *screening* tool, not an operational collision-avoidance product. It uses TLE-only orbit estimates without real covariance data. Production-grade conjunction analysis requires Conjunction Data Messages (CDMs) and proper covariance propagation that only operators / 18 SDS provide.

## What it does

- Fetches public TLE catalogs every 4 hours (CelesTrak `active` group).
- Propagates each satellite with **SGP4** over a 72-hour horizon.
- Detects close approaches with a tiered screening pipeline (perigee/apogee filter -> coarse 60 s sweep -> sub-second TCA refinement) so 30 000+ objects can be screened in minutes on a single core.
- Plots every conjunction at the **real WGS-84 sub-satellite point of both objects at TCA**, with a polyline drawn between them. No fictitious markers.
- Stores everything in PostgreSQL (TimescaleDB-friendly schema).
- Exposes a clean REST API for both casual and operator-grade use:
  - `/api/health`, `/api/stats` - liveness + dashboard summaries.
  - `/api/satellites`, `/api/satellites/{id}` - catalogue browse + permalink for any satellite.
  - `/api/conjunctions` - JSON list with sub-satellite points at TCA.
  - `/api/conjunctions.csv` - same data as a spreadsheet download.
  - `/api/calendar.ics` - **RFC 5545 calendar feed**; subscribe from Google / Outlook / Apple Calendar so close approaches show up next to your meetings.
  - `/api/heatmap/*` - altitude x inclination congestion matrix and 30-day conjunction-count timeline.
  - `/api/alerts/subscriptions` - register a **webhook or email** to be notified when one of *your* satellites has a close approach.
- Serves a Vue 3 dashboard with a Cesium globe, live stats, sortable conjunctions table, satellite search bar with permalink pages, congestion heatmap, alerts page, and one-click CSV / iCal export.

## Architecture

```
                     CelesTrak / Space-Track       (every 4 h)
                                |
                                v
   +----------------------------+----------------------------+
   |  Backend  (Python 3.12 / FastAPI)                       |
   |    domain   -> entities (Satellite, TLE, Conjunction)   |
   |    application -> use cases / services                  |
   |    infrastructure -> sgp4, httpx fetchers, SQLAlchemy   |
   +----------------------------+----------------------------+
                                |
                  PostgreSQL (TLEs, satellites, conjunctions)
                                |
                                v
   +----------------------------+----------------------------+
   |  Frontend (Vue 3 / TypeScript)                          |
   |    Composables + Pinia + Vue Query (cache)              |
   |    PrimeVue 4 (Aura) + Tailwind v4                      |
   |    Cesium 3D globe (lazy-loaded)                        |
   +---------------------------------------------------------+
```

The backend follows a **hexagonal architecture**: the domain layer knows nothing about HTTP, SQL, or sgp4. Ports describe what the application needs (a `TLERepository`, a `Propagator`, a `TLESource`); adapters are concrete implementations injected at startup.

## Quick start

### Run the whole stack with Docker

```sh
git clone https://github.com/tanguychenier/Orbital-Collision-Risk-Dashboard.git
cd Orbital-Collision-Risk-Dashboard
cp .env.example .env
docker compose up -d
```

Open:

- **Dashboard**: <http://localhost:5173>
- **API docs (Swagger)**: <http://localhost:8000/docs>

### Run each side standalone

```sh
# Backend (Python 3.12+, uv or pip)
cd backend
uv sync               # or: pip install -e .[dev]
uv run uvicorn oc.main:app --reload

# Frontend (Node 20+, pnpm)
cd frontend
pnpm install
pnpm dev              # http://localhost:5173 with MSW fixtures by default
```

The frontend ships with [Mock Service Worker](https://mswjs.io/) fixtures, so you can run it **without** the backend (`VITE_USE_MSW=true`).

## API quickstart

No API key required. Examples use `httpie`-friendly syntax; `curl` works the same.

```sh
# JSON list of upcoming conjunctions, sub-satellite point at TCA included.
curl 'http://localhost:8000/api/conjunctions?max_distance_km=5&hours=72'

# Spreadsheet-friendly CSV with the same columns.
curl -OJ 'http://localhost:8000/api/conjunctions.csv?max_distance_km=5&hours=168'

# iCalendar feed for the satellites you care about. Add this URL as a
# new calendar in Google / Outlook / Apple Calendar:
# http://localhost:8000/api/calendar.ics?norad_id=25544&norad_id=44713&hours=168
curl 'http://localhost:8000/api/calendar.ics?norad_id=25544&hours=168'

# Subscribe a webhook for one of your satellites.
curl -X POST http://localhost:8000/api/alerts/subscriptions \
  -H 'content-type: application/json' \
  -d '{"email_or_webhook_url":"https://hooks.slack.com/...","norad_ids":[25544],"miss_distance_km_threshold":5}'
```

The full schema is browsable at `/docs` (Swagger UI) and `/redoc`.

## Testing

| Layer | Command | What it covers |
| --- | --- | --- |
| Backend unit + API | `cd backend && uv run pytest -q` | Propagation accuracy, conjunction screening, TLE parsing, every API endpoint |
| Frontend unit | `cd frontend && pnpm test` | Composables, Pinia stores, components (sorting, pagination, etc.) |
| Frontend e2e | `cd frontend && pnpm test:e2e` | Playwright across **mobile / tablet / desktop** viewports + axe-core a11y check |
| Lint | `cd backend && uv run ruff check && cd ../frontend && pnpm lint` | Linters and formatters everywhere |
| Type-check | `uv run mypy src` (backend) / `pnpm typecheck` (frontend) | Strict typing both sides |

Detailed guides live under [`docs/`](docs/):

- [`docs/architecture.md`](docs/architecture.md) - hexagonal layout, port/adapter mapping, request flow.
- [`docs/contributing.md`](docs/contributing.md) - dev setup, code style, Conventional Commits, PR checklist.
- [`docs/data-sources.md`](docs/data-sources.md) - CelesTrak rate limits, Space-Track alternative, TLE accuracy caveats.
- [`SECURITY.md`](SECURITY.md) - responsible-disclosure policy.
- [`CHANGELOG.md`](CHANGELOG.md) - release history (Keep a Changelog).

## Project layout

```
Orbital-Collision-Risk-Dashboard/
├── docker-compose.yml          # postgres + backend + frontend
├── .env.example
├── README.md / LICENSE
├── docs/
│   └── api-contract.md
├── backend/
│   ├── pyproject.toml          # ruff, mypy strict, pytest
│   ├── Dockerfile
│   ├── alembic/                # migrations
│   ├── src/oc/
│   │   ├── main.py             # FastAPI app factory
│   │   ├── domain/             # entities + value objects (no framework imports)
│   │   ├── application/        # ports (Protocols) + use cases
│   │   ├── infrastructure/     # http, persistence (SQLAlchemy), propagation (sgp4 + geodetic), tle_sources, scheduler, alerts
│   │   └── interface/          # Pydantic schemas (HTTP boundary)
│   └── tests/                  # pytest, in-memory SQLite for fast feedback
├── frontend/
│   ├── package.json            # pnpm
│   ├── Dockerfile + nginx.conf
│   ├── vite.config.ts
│   ├── playwright.config.ts    # mobile / tablet / desktop projects
│   ├── src/
│   │   ├── api/                # axios client + endpoints
│   │   ├── stores/             # Pinia
│   │   ├── composables/        # cross-component logic
│   │   ├── services/cesium.ts  # lazy-loaded 3D globe
│   │   ├── components/         # presentational
│   │   └── views/Dashboard.vue
│   ├── public/                 # static assets (Cesium NaturalEarthII tile, favicon)
│   ├── tests/unit/             # Vitest
│   └── e2e/                    # Playwright across {chrome,edge,firefox} x {mobile,tablet,desktop}
└── .github/workflows/ci.yml    # lint + typecheck + tests on every PR
```

## Configuration

All settings come from `.env` (see `.env.example`). The most important ones:

| Variable | Default | Purpose |
| --- | --- | --- |
| `OC_DATABASE_URL` | sqlite-aiosqlite for tests | Async DSN consumed by SQLAlchemy |
| `OC_ENABLE_SCHEDULER` | `false` | Set `true` to launch the background TLE refresh + conjunction recompute |
| `OC_LOG_LEVEL` | `info` | `debug` / `info` / `warning` |
| `VITE_API_BASE_URL` | `http://localhost:8000/api` | Where the frontend hits the backend |
| `VITE_USE_MSW` | `false` | Set `true` to demo the dashboard without a backend |

## Best practices

This is a showcase project, so it sticks to:

- **Hexagonal architecture** on the backend (ports + adapters). The domain code never imports a framework or driver.
- **Clean code**: small functions, descriptive names, no comments that restate the code.
- **SOLID**: dependency inversion via FastAPI's `Depends`, single-responsibility services, open/closed adapters (you can swap CelesTrak for Space-Track without touching the use case).
- **Strict typing**: `mypy --strict` (backend), `vue-tsc` strict (frontend).
- **Linters / formatters**: `ruff` + `mypy` (backend), `eslint` + `prettier` (frontend), all wired into pre-commit + CI.
- **Cross-platform**: everything runs in containers; the development scripts work on Windows, macOS and Linux.
- **Accessibility**: axe-core asserts no critical/serious a11y issues across the 3 viewports.
- **Internationalisation-ready**: `vue-i18n` is wired even though we only ship English (adding French is a one-file change).

## Limitations & honesty

- TLEs are typically only good to ~1 km accuracy and degrade after 5-7 days. For high-traffic constellations like Starlink (which manoeuvre often), predictions older than 12 h are unreliable.
- The "probability of collision" column is a **screening proxy** based on a fixed 1-sigma covariance. **It is not a Pc**.
- Mega-constellations push the all-pairs problem rapidly into the millions of pairs - the screening tier filtering keeps it tractable on commodity hardware but is not a substitute for proper operator-level CDMs.

## References

- Hoots, F. and Roehrich, R. *Models for Propagation of NORAD Element Sets* (Spacetrack Report 3).
- Vallado, D. *Fundamentals of Astrodynamics and Applications*.
- Healy, L. *Close conjunction detection on parallel computers* (1995) - the tier-filter pipeline used here.
- CelesTrak: <https://celestrak.org/>
- Space-Track: <https://www.space-track.org/>
- Cesium documentation: <https://cesium.com/learn/cesiumjs/>

## Licence

MIT - see [`LICENSE`](LICENSE).

## Author

Built and maintained by [**Tansoftware**](https://www.tansoftware.com) - **Tanguy Chénier**.

- Company: <https://www.tansoftware.com>
- LinkedIn: <https://www.linkedin.com/in/tanguy-chenier/>
- GitHub organisation: [@Tan-Software](https://github.com/Tan-Software)
- GitHub personal (latest tools): [@tanguychenier](https://github.com/tanguychenier)
