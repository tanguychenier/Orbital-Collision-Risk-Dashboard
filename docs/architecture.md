# Architecture

The backend follows a strict **hexagonal (ports-and-adapters)
architecture**. The domain knows nothing about HTTP, SQL, or sgp4. The
application layer expresses every use case in terms of port protocols.
The infrastructure layer is the only place where third-party drivers
are imported. The composition root in `oc.main` wires concrete adapters
into FastAPI dependencies.

## Hexagonal layout

```mermaid
flowchart TB
    subgraph Inbound[Inbound adapters]
        HTTP[HTTP / FastAPI routers]
        SCH[APScheduler periodic jobs]
    end

    subgraph App[Application layer - use cases]
        UC1[refresh_tles]
        UC2[compute_conjunctions]
    end

    subgraph Ports[Application ports - Protocol classes]
        P1[TLESource]
        P2[TLERepository]
        P3[ConjunctionRepository]
        P4[Propagator]
        P5[BoundedScalarMinimizer]
        P6[Clock]
    end

    subgraph Domain[Domain layer - pure Python]
        E1[Satellite / TLE / Conjunction]
        V1[Ephemeris / OrbitalElements / CandidateInterval]
    end

    subgraph Outbound[Outbound adapters]
        DB[SQLAlchemy + PostgreSQL]
        SGP4[sgp4 propagator]
        SCIPY[scipy bounded minimizer]
        HTTPX[httpx CelesTrak client]
    end

    HTTP --> UC1
    HTTP --> UC2
    SCH --> UC1
    SCH --> UC2

    UC1 --> P1
    UC1 --> P2
    UC2 --> P2
    UC2 --> P3
    UC2 --> P4
    UC2 --> P5

    UC1 --> Domain
    UC2 --> Domain

    P1 -. implemented by .-> HTTPX
    P2 -. implemented by .-> DB
    P3 -. implemented by .-> DB
    P4 -. implemented by .-> SGP4
    P5 -. implemented by .-> SCIPY
```

## Port / adapter mapping

| Port (`oc.application.ports`)         | Concrete adapter (`oc.infrastructure`)                          |
| ------------------------------------- | --------------------------------------------------------------- |
| `TLESource.fetch`                     | `tle_sources.celestrak.CelestrakTLESource`                      |
| `TLERepository.upsert_parsed_tles`    | `persistence.tle_repository.SQLAlchemyTLERepository`            |
| `TLERepository.latest_tle_per_active_satellite` | `persistence.tle_repository.SQLAlchemyTLERepository`  |
| `Propagator.propagate` / `.orbital_elements` | `propagation.sgp4_propagator.SGP4Propagator`             |
| `BoundedScalarMinimizer.minimize`     | `numerics.scipy_minimizer.ScipyBoundedMinimizer`                |
| `Clock.now`                           | `datetime.now(UTC)` (no dedicated adapter shipped yet)          |

## Request flow: `GET /api/conjunctions`

```mermaid
sequenceDiagram
    participant Browser
    participant Router as oc.infrastructure.http.conjunctions
    participant Session as AsyncSession (SQLAlchemy)
    participant DB as PostgreSQL

    Browser->>Router: GET /api/conjunctions?max_distance_km=5&hours=72
    Router->>Router: build SELECT with bind params and pagination
    Router->>Session: execute(stmt)
    Session->>DB: SELECT ... FROM conjunctions ... ORDER BY tca
    DB-->>Session: rows
    Session-->>Router: ORM Conjunction[]
    Router->>Router: map to ConjunctionListItem (Pydantic schema)
    Router-->>Browser: 200 application/json
```

The list endpoint reads from the materialised `conjunctions` table
populated by the scheduled `compute_conjunctions` use case. The detail
endpoint follows the same pattern but eager-loads the originating TLEs.

## Composition root

```mermaid
flowchart LR
    Settings[(.env)] --> Main[oc.main.create_app]
    Main --> Router[build_api_router]
    Main -->|on lifespan startup| Sched[build_scheduler]
    Sched --> UC1
    Sched --> UC2
    Router --> UC2
```

`create_app` is the only place where adapters and use cases meet. Tests
override `Settings`, replace the database engine with an in-memory
SQLite, and never need to touch the use cases directly.

## Why hexagonal here?

- **Replaceable adapters.** Swapping CelesTrak for Space-Track means
  writing a new `TLESource` adapter; the use case is untouched.
- **Fast tests.** The 28-test backend suite runs in ~3 seconds against
  in-memory SQLite. The screening tests bypass HTTP entirely by
  calling the use case with a fake propagator state.
- **Honest dependency graph.** `mypy --strict` enforces that nothing in
  `oc.domain` or `oc.application` imports SQLAlchemy, FastAPI, sgp4,
  scipy, or httpx.
