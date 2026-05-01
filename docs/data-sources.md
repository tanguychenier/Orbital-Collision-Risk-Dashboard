# Data sources

The dashboard ingests **public** Two-Line Element (TLE) catalogs only.
This document tracks the sources we support, their access policies, and
the well-known accuracy caveats that bound what the screening pipeline
can usefully tell you.

## CelesTrak (default)

[CelesTrak](https://celestrak.org/) is the project's default source. We
hit the gp.php endpoint with the `active` group:

```
https://celestrak.org/NORAD/elements/gp.php?GROUP=active&FORMAT=tle
```

CelesTrak republishes the public 18 SDS catalog. There is **no
authentication** required.

### Rate limits and best practices

CelesTrak does not document hard rate limits but enforces a soft policy
of **one fetch every ~2 hours per group**. The defaults shipped in
`oc.config.Settings` align with that:

- `tle_refresh_interval_hours = 4.0`
- `http_timeout_seconds = 30.0`

Send a descriptive `User-Agent` header, do not poll faster than the
documented epoch cadence (~6 h on the catalog), and cache aggressively.

If you mirror the catalog (e.g. for a CI pipeline) please honour
[CelesTrak's request to use the documented endpoints](https://celestrak.org/NORAD/elements/)
rather than scraping the HTML index.

## Space-Track (alternative, requires account)

[Space-Track](https://www.space-track.org/) offers the **authoritative**
public catalog with deeper history (Conjunction Data Messages, full
catalog dumps, decay events). It requires:

1. An account approved by the 18 SDS (free, takes a few business days).
2. Cookie-based authentication (`POST /ajaxauth/login`, then session
   cookie on subsequent requests).
3. Compliance with the
   [Space-Track API Terms of Use](https://www.space-track.org/documentation#/api),
   in particular the **30 requests / minute** rate limit.

Swapping to Space-Track is a single-adapter change: implement
`oc.application.ports.TLESource` against the Space-Track HTTP API. The
existing `refresh_tles_from_url` use case remains unchanged.

## TLE accuracy caveats

TLEs are **fitted approximations** of an orbit, not measured truth.
Operationally:

- **Cross-track / radial position error** is typically **~1 km** at
  epoch and degrades roughly linearly with age.
- **Predicted error** beyond **5-7 days** of propagation is dominated by
  unmodelled atmospheric drag. For Starlink and other low-altitude
  manoeuvring constellations, a **12-hour** window is the safe upper
  bound.
- The SGP4 propagator implements the WGS-72 gravity model; it does
  **not** model lunisolar perturbations beyond the analytic
  approximations in Spacetrack Report 3.
- Manoeuvring objects (ISS reboosts, Starlink station-keeping) violate
  the SGP4 force model; their TLEs are stale within hours of a burn.

## Why this matters for the dashboard

The screening probability we expose is a **Gaussian on miss distance**,
not a true probability of collision. To compute a real *Pc* you need:

1. Position covariance for both objects (not in TLEs).
2. Time-correlated covariance propagation.
3. Object physical dimensions (hard-body radius).

Operators receive these via Conjunction Data Messages (CDMs) issued by
18 SDS / Space-Track. Producing CDMs is out of scope for a public
screening dashboard; the goal of this project is to surface
**candidates** worth a closer look, not to replace operator-grade
analysis.

## References

- Hoots, F. and Roehrich, R. *Models for Propagation of NORAD Element
  Sets* (Spacetrack Report 3).
- Vallado, D. *Fundamentals of Astrodynamics and Applications*.
- CelesTrak: <https://celestrak.org/>
- Space-Track: <https://www.space-track.org/>
