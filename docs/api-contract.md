# Orbital Conjunctions Dashboard — API Contract v0

All endpoints under `/api`. JSON in/out. CORS allowed for any origin in dev.

## Health

```
GET /api/health
=> 200 { "status": "ok", "version": "0.1.0", "tle_age_hours": 3.2 }
```

## Statistics

```
GET /api/stats
=> 200 {
  "total_satellites": 8421,
  "total_active": 7833,
  "tle_last_updated": "2026-05-01T08:00:00Z",
  "conjunctions_24h": 142,
  "conjunctions_72h": 421,
  "high_risk_24h": 3            // miss < 1 km
}
```

## Satellites

```
GET /api/satellites?q=starlink&limit=50&offset=0
=> 200 [
  { "norad_id": 44713, "name": "STARLINK-1007", "country": "US",
    "type": "PAYLOAD", "launch_date": "2019-11-11" }
]
```

## Conjunctions

Time-of-Closest-Approach is in UTC. Miss distance in kilometers.
Relative velocity in km/s. Probability is computed from a fixed 1-sigma
covariance assumption (configurable, documented as approximate).

```
GET /api/conjunctions?max_distance_km=5&hours=72&limit=200&offset=0
=> 200 [
  { "id": "0a9b...",
    "sat_a": { "norad_id": 44713, "name": "STARLINK-1007" },
    "sat_b": { "norad_id": 50189, "name": "ONEWEB-0421"  },
    "tca": "2026-05-02T03:42:11Z",
    "miss_distance_km": 0.84,
    "relative_velocity_km_s": 13.2,
    "probability": 0.0021,
    "computed_at": "2026-05-01T08:05:00Z" }
]

GET /api/conjunctions/{id}
=> 200 {
  "id": "...",
  "sat_a": { /* full satellite */ },
  "sat_b": { /* full satellite */ },
  "tca": "...", "miss_distance_km": 0.84,
  "relative_velocity_km_s": 13.2, "probability": 0.0021,
  "tle_a_line1": "1 44713U ...", "tle_a_line2": "2 44713 ...",
  "tle_b_line1": "1 50189U ...", "tle_b_line2": "2 50189 ..."
}
```

## Errors

Standard FastAPI errors. Always JSON:
`{"detail": "<message>"}` with appropriate 4xx/5xx code.
