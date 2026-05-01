# Changelog

All notable changes to this project are documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Strict hexagonal architecture on the backend (`domain` / `application`
  / `infrastructure` / `interface` packages).
- `application/ports.py` declaring the `TLESource`, `TLERepository`,
  `ConjunctionRepository`, `Propagator`, `BoundedScalarMinimizer`, and
  `Clock` Protocol-typed ports.
- `docs/architecture.md`, `docs/contributing.md`, `docs/data-sources.md`.
- `SECURITY.md` with a 90-day coordinated disclosure policy.
- `CHANGELOG.md` (this file).
- `.editorconfig` for consistent editor settings.
- `.dockerignore` for backend and frontend images.
- `.github/dependabot.yml` covering pip, npm, GitHub Actions, and Docker.
- `.pre-commit-config.yaml` running ruff, mypy, eslint, prettier,
  markdownlint.

### Changed

- The HTTP routers now live under `oc.infrastructure.http`; the legacy
  `oc.api.*` paths remain importable through compatibility shims.
- The SGP4 propagator and the SQLAlchemy persistence layer were
  isolated behind ports; the screening pipeline now takes a
  `Propagator` and a `BoundedScalarMinimizer` as injected dependencies.

## [0.1.0] - 2026-05-01

### Added

- Initial release of the Orbital Collision Risk Dashboard.
- FastAPI backend with `/api/health`, `/api/stats`, `/api/satellites`,
  `/api/conjunctions[/{id}]` endpoints.
- SGP4 propagation, three-tier conjunction screening pipeline
  (perigee/apogee filter, coarse 60 s sweep, sub-second TCA refinement).
- CelesTrak TLE ingestion with idempotent persistence.
- APScheduler-based periodic TLE refresh and conjunction recompute.
- Vue 3 + TypeScript dashboard with PrimeVue, Tailwind v4, Pinia, Vue
  Query, vue-i18n, and a lazy-loaded Cesium globe.
- Mock Service Worker fixtures for backend-less demos.
- Vitest unit tests, Playwright e2e tests with axe-core a11y checks
  across mobile / tablet / desktop viewports.
- Strict typing (`mypy --strict`, `vue-tsc`) and linters (`ruff`,
  `eslint`, `prettier`).
- Multi-stage Docker images for backend and frontend; `docker-compose`
  for the full stack.
- GitHub Actions CI running lint + typecheck + tests on every PR.

[Unreleased]: https://github.com/Tan-Software/Orbital-Collision-Risk-Dashboard/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/Tan-Software/Orbital-Collision-Risk-Dashboard/releases/tag/v0.1.0
