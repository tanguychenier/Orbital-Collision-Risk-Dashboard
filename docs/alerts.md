# Conjunction alert subsystem

The Orbital Collision Risk Dashboard ships a webhook-based alert
subsystem aimed at small-satellite operators. A subscription is a
standing request to be notified -- via Discord webhook, generic webhook,
or email -- whenever a predicted close approach drops below a
miss-distance threshold for any of the satellites the operator watches.

## Privacy stance

The subsystem is **deliberately stateless**:

- We do not maintain user accounts, sessions, or login flows.
- We do not associate a subscription with anything beyond the target
  webhook URL or email address it was created with.
- The only credential is the **secret token** returned at subscription
  time. It is embedded in the *manage URL* we hand back. Lose the URL
  and you lose the ability to inspect or unsubscribe -- we cannot
  recover it for you. Save it.

This stance is enforced at the API surface:

- `POST /api/alerts/subscriptions` returns `{ id, manage_url }`. The
  token never appears in any other payload.
- `GET /api/alerts/subscriptions/{id}?token=...` returns the
  subscription **only** when the token matches; otherwise a flat 404.
- `DELETE /api/alerts/subscriptions/{id}?token=...` is the only way to
  unsubscribe (soft-delete: `is_active=False`).

## Webhook payload (Discord-compatible)

When an alert fires, the backend POSTs a JSON body to the configured
URL. The payload is shaped to drop unmodified into a Discord
`Incoming Webhook`:

```json
{
  "content": "Conjunction alert: OPERATOR-SAT (42001) <-> DEBRIS-X (42002) at 2026-05-08T12:00:00+00:00 (miss 1.234 km, threshold 5.00 km)",
  "embeds": [
    {
      "title": "Orbital conjunction alert",
      "description": "Conjunction alert: OPERATOR-SAT (42001) <-> DEBRIS-X (42002) at 2026-05-08T12:00:00+00:00 (miss 1.234 km, threshold 5.00 km)",
      "fields": [
        { "name": "Satellite A", "value": "OPERATOR-SAT (42001)", "inline": true },
        { "name": "Satellite B", "value": "DEBRIS-X (42002)", "inline": true },
        { "name": "TCA (UTC)", "value": "2026-05-08T12:00:00+00:00", "inline": false },
        { "name": "Miss distance (km)", "value": "1.234", "inline": true },
        { "name": "Relative velocity (km/s)", "value": "14.100", "inline": true },
        { "name": "Probability", "value": "0.4", "inline": true }
      ]
    }
  ]
}
```

Generic webhook receivers can ignore the `embeds` array and rely on the
flat `content` line, which is a self-contained one-line summary.

For email subscribers we send a plain-text message with the same
summary as the body and `Orbital conjunction alert` as the subject. The
delivery uses `smtplib` and is enabled only when the `OC_SMTP_HOST`
environment variable is set. Without SMTP configured, email targets are
logged but no email is actually sent (the loop never errors out).

## Cadence and idempotency

The alert dispatch loop runs from APScheduler **every 15 minutes**
(`OC_ALERTS_NOTIFY_INTERVAL_MINUTES`). For every active subscription it
queries the `conjunctions` table over a **7-day horizon**
(`OC_ALERTS_HORIZON_DAYS`) and emits one notification per matching
conjunction id that has not already been delivered to that subscription.
The deduplication is enforced through the
`alert_subscription_deliveries` table, so re-running the loop is safe.

## Rate limits and best practices

- **Threshold sanity.** Set the threshold close to your operational
  risk envelope (typically 1-5 km for LEO). Too high a threshold can
  flood the channel.
- **Per-subscription size.** A single subscription can watch up to
  **50 NORAD ids**. Operators with bigger constellations should split
  the catalogue across multiple subscriptions, ideally one per ground
  station or shift rotation.
- **Discord rate limiting.** Discord enforces ~30 messages per minute
  per webhook. Our 15-minute cadence keeps you well below that even
  for hot conjunction periods, but a constellation with thousands of
  active conjunctions should subscribe with a higher threshold first.
- **Webhook secrecy.** The webhook URL acts as a bearer token for any
  client that knows it. Rotate it on the Discord/Slack side
  immediately if you suspect leakage and re-subscribe.
- **Email deliverability.** Configure `OC_SMTP_FROM_ADDRESS` to a
  domain you control to avoid being flagged as spam.

## Configuration reference

| Environment variable                 | Default                                | Purpose                                              |
| ------------------------------------ | -------------------------------------- | ---------------------------------------------------- |
| `OC_ALERTS_BASE_URL`                 | `http://localhost:8000`                | Base used to render the manage URL                   |
| `OC_ALERTS_HORIZON_DAYS`             | `7.0`                                  | How far ahead to look for matching conjunctions      |
| `OC_ALERTS_NOTIFY_INTERVAL_MINUTES`  | `15.0`                                 | Cadence of the dispatch loop                         |
| `OC_SMTP_HOST`                       | unset                                  | SMTP server hostname (email enabled iff set)         |
| `OC_SMTP_PORT`                       | `587`                                  | SMTP server port                                     |
| `OC_SMTP_USERNAME` / `_PASSWORD`     | unset                                  | Optional SMTP credentials (STARTTLS used if both set)|
| `OC_SMTP_FROM_ADDRESS`               | `alerts@orbital-conjunctions.local`    | `From:` header used in outbound emails               |
