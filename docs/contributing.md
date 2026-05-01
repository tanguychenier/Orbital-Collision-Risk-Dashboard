# Contributing

Thanks for taking the time to contribute. The project is a showcase of
clean code, hexagonal architecture, and disciplined testing -- those
are the bars every PR is held to.

## Development setup

### Prerequisites

- Python 3.12 or newer
- Node.js 20 or newer
- pnpm 9
- Docker (for the optional full-stack run)

### Bootstrap

```sh
git clone https://github.com/Tan-Software/Orbital-Collision-Risk-Dashboard.git
cd Orbital-Collision-Risk-Dashboard

# Backend
cd backend
python -m venv .venv && source .venv/bin/activate     # or `.venv\Scripts\activate` on Windows
pip install -e .[dev]

# Frontend
cd ../frontend
pnpm install
pnpm test:e2e:install                                  # installs Playwright Chromium
```

## Running the test suites

| Layer            | Command                                       | What it covers                                |
| ---------------- | --------------------------------------------- | --------------------------------------------- |
| Backend          | `cd backend && pytest -q`                     | Use cases, propagation accuracy, API tests    |
| Backend lint     | `cd backend && ruff check && ruff format --check src tests` | Style and layout                |
| Backend types    | `cd backend && mypy src`                      | `--strict` enforced via `pyproject.toml`      |
| Frontend unit    | `cd frontend && pnpm test`                    | Vitest (composables, stores, components)      |
| Frontend lint    | `cd frontend && pnpm lint`                    | ESLint + Prettier                             |
| Frontend types   | `cd frontend && pnpm typecheck`               | `vue-tsc --build`                             |
| Frontend e2e     | `cd frontend && pnpm test:e2e`                | Playwright + axe-core a11y                    |

All of these are also run by the GitHub Actions workflow on every PR.

## Code style

### Python

- Line length: 100 characters.
- Docstrings: Google style. Every public function / class **must** have
  at least a one-line summary. Use cases and ports get full docstrings
  (Args / Returns / Raises).
- Magic literals are forbidden -- promote them to `_CONSTANT_CASE`
  module-level names with a comment explaining the choice.
- The domain layer never imports SQLAlchemy, FastAPI, sgp4, scipy, or
  httpx. The application layer never imports them either; it only
  depends on `oc.domain` and `oc.application.ports`.

### TypeScript / Vue

- Prettier defaults; ESLint via `@vue/eslint-config-typescript`.
- Pinia stores expose a typed `state` and named actions; they never
  call axios directly -- always go through `src/api/`.
- Composables prefix with `use*`, return refs / computed, and stay
  under 50 lines.

## Commit messages -- Conventional Commits

Every commit message must follow the
[Conventional Commits](https://www.conventionalcommits.org/) spec:

```
<type>(<scope>): <short summary>

<optional body explaining the why>
```

Common types:

- `feat`: a new user-visible feature.
- `fix`: a user-visible bug fix.
- `refactor`: code restructuring with no behaviour change.
- `docs`: documentation only.
- `chore`: build, deps, scaffolding, no source change.
- `test`: tests only.
- `ci`: GitHub Actions / pipelines.
- `perf`: performance improvement.

Scopes used in this repo: `backend`, `frontend`, `docs`, `architecture`,
`security`, `ci`, `infra`, `deps`.

## Pull-request checklist

Before clicking **Ready for review**:

- [ ] All tests pass locally (`pytest -q`, `pnpm test`, `pnpm test:e2e`).
- [ ] `ruff check`, `ruff format --check`, `mypy src` all pass.
- [ ] `pnpm lint` and `pnpm typecheck` pass.
- [ ] Public functions have docstrings; new constants are named.
- [ ] No SQLAlchemy / FastAPI / sgp4 import added in `oc.domain` or
      `oc.application`.
- [ ] `docs/` updated if the change affects the API contract or the
      hexagonal layout.
- [ ] `CHANGELOG.md` has an `Unreleased` entry.

Pre-commit takes care of most of these locally. Install it once with:

```sh
pip install pre-commit && pre-commit install
```

## Reporting bugs

Use the [GitHub issue tracker](https://github.com/Tan-Software/Orbital-Collision-Risk-Dashboard/issues).
Include:

- The exact command that reproduces the bug.
- The expected vs observed behaviour.
- The OS / Python / Node version.

For **security** vulnerabilities, follow the disclosure process in
[`SECURITY.md`](../SECURITY.md) instead.
