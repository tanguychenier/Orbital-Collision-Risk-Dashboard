# Orbital Conjunctions - Frontend

Public dashboard surfacing real-time satellite collision risks.

## Stack

- **Vue 3** + **TypeScript (strict)** + **Vite**
- **Pinia** state, **Vue Router 4**, **Vue Query** for server state
- **PrimeVue 4** (Aura preset) + **Tailwind CSS v4**
- **CesiumJS** lazy-loaded for the 3D globe
- **MSW** (Mock Service Worker) for offline-friendly fixtures
- **Vitest** + **@vue/test-utils** + **@testing-library/vue** unit tests
- **Playwright** + **@axe-core/playwright** end-to-end tests across 3 viewports
- **ESLint** + **Prettier** + **Husky** + **lint-staged** pre-commit hooks

## Getting started

```bash
pnpm install
pnpm dev          # http://localhost:5173 - serves with MSW fixtures by default
pnpm test         # Vitest unit tests
pnpm test:e2e     # Playwright (run pnpm exec playwright install --with-deps chromium first)
pnpm typecheck
pnpm lint
pnpm build        # production build
```

### Environment variables

- `VITE_API_BASE_URL` - defaults to `/api` (used when MSW is disabled).
- `VITE_USE_MSW` - set to `false` to bypass the mock layer and hit the real backend.
- `VITE_CESIUM_ION_TOKEN` - optional Cesium Ion access token for high-resolution imagery.

## Project layout

```
frontend/
├── src/
│   ├── api/            axios client + endpoint wrappers
│   ├── stores/         Pinia stores (theme, conjunctions filters)
│   ├── composables/    cross-cutting reactive logic (useTheme, useViewport, useStats, ...)
│   ├── services/       lazy-loaded heavy services (Cesium globe)
│   ├── components/     presentational components
│   ├── views/          routed pages (Dashboard)
│   ├── mocks/          MSW handlers + fixtures
│   └── styles/         Tailwind entry
├── tests/unit/         Vitest unit tests
└── e2e/                Playwright cross-viewport e2e
```

## Authoring

Built by **Tansoftware** - author **Tanguy Chénier**:

- LinkedIn: https://www.linkedin.com/in/tanguy-chenier/
- GitHub @Tan-Software: https://github.com/Tan-Software
- GitHub @tanguychenier (latest tools): https://github.com/tanguychenier
- Web: https://tansoftware.com
