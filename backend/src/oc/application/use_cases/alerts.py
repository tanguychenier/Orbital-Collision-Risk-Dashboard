"""Use cases for the webhook-based alert subsystem.

The subsystem is intentionally stateless: there are no user accounts.
The ``secret_token`` returned at subscription time is the only credential
required to inspect or unsubscribe. Three operations are exposed:

* :func:`subscribe_to_alerts`
* :func:`unsubscribe_from_alerts`
* :func:`notify_pending_alerts`

The functions depend exclusively on the
:mod:`oc.application.ports` Protocols, never on the SQLAlchemy adapters.
"""

from __future__ import annotations

import logging
import re
import secrets
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta

from oc.application.ports import (
    AlertNotifier,
    AlertSubscriptionRepository,
    ConjunctionAlertSource,
)
from oc.domain.entities import AlertSubscription

logger = logging.getLogger(__name__)


# A pragmatic email regex: acceptable for the "looks like an email" heuristic
# on the inbound HTTP boundary. Final delivery uses ``smtplib`` which performs
# the actual addressing, so we do not need RFC-5322 strict parsing here.
_EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$")
_WEBHOOK_RE = re.compile(r"^https?://[A-Za-z0-9._\-]+(:\d+)?(/.*)?$")

# Default upper bounds aligned with the API contract.
_MIN_THRESHOLD_KM: float = 0.1
_MAX_THRESHOLD_KM: float = 50.0
_MAX_NORAD_IDS: int = 50


class AlertValidationError(ValueError):
    """Raised when a subscription payload fails domain validation."""


@dataclass(frozen=True)
class SubscriptionRequest:
    """Inbound payload for :func:`subscribe_to_alerts`.

    Pre-validated at the HTTP boundary by Pydantic; this dataclass keeps
    the use case independent of the web framework and re-runs the domain
    invariants for defensive in-process callers.
    """

    email_or_webhook_url: str
    norad_ids: tuple[int, ...]
    miss_distance_km_threshold: float


@dataclass(frozen=True)
class SubscriptionResult:
    """Return value of :func:`subscribe_to_alerts`."""

    subscription: AlertSubscription
    manage_url: str


def _validate_target(target: str) -> None:
    """Reject targets that look like neither a URL nor an email."""
    target = target.strip()
    if not target:
        raise AlertValidationError("email_or_webhook_url must not be empty")
    if _WEBHOOK_RE.match(target) is None and _EMAIL_RE.match(target) is None:
        raise AlertValidationError(
            "email_or_webhook_url must be an http(s) URL or a valid email address"
        )


def _validate_norad_ids(norad_ids: tuple[int, ...]) -> None:
    """Reject empty or oversized NORAD id lists."""
    if not norad_ids:
        raise AlertValidationError("at least one NORAD id is required")
    if len(norad_ids) > _MAX_NORAD_IDS:
        raise AlertValidationError(f"at most {_MAX_NORAD_IDS} NORAD ids per subscription")
    if any(n <= 0 for n in norad_ids):
        raise AlertValidationError("NORAD ids must be positive integers")


def _validate_threshold(threshold: float) -> None:
    """Reject thresholds outside the [0.1, 50] km range."""
    if threshold < _MIN_THRESHOLD_KM or threshold > _MAX_THRESHOLD_KM:
        raise AlertValidationError(
            f"miss_distance_km_threshold must lie in [{_MIN_THRESHOLD_KM}, {_MAX_THRESHOLD_KM}]"
        )


def _build_manage_url(base_url: str, subscription_id: str, secret_token: str) -> str:
    """Render the manage URL embedded in the response body."""
    return f"{base_url.rstrip('/')}/alerts/{subscription_id}?token={secret_token}"


async def subscribe_to_alerts(
    request: SubscriptionRequest,
    repository: AlertSubscriptionRepository,
    base_url: str,
    now: datetime,
) -> SubscriptionResult:
    """Validate the request, persist the subscription, and return the manage URL."""
    _validate_target(request.email_or_webhook_url)
    _validate_norad_ids(request.norad_ids)
    _validate_threshold(request.miss_distance_km_threshold)

    subscription = AlertSubscription(
        id=uuid.uuid4().hex,
        email_or_webhook_url=request.email_or_webhook_url.strip(),
        norad_ids=tuple(int(n) for n in request.norad_ids),
        miss_distance_km_threshold=float(request.miss_distance_km_threshold),
        created_at=now,
        secret_token=secrets.token_urlsafe(32),
        last_notified_at=None,
        is_active=True,
    )
    await repository.add(subscription)
    return SubscriptionResult(
        subscription=subscription,
        manage_url=_build_manage_url(base_url, subscription.id, subscription.secret_token),
    )


async def unsubscribe_from_alerts(
    subscription_id: str,
    token: str,
    repository: AlertSubscriptionRepository,
) -> bool:
    """Soft-delete the subscription if ``token`` matches.

    Returns ``True`` on success; ``False`` if the id is unknown or the
    token doesn't match. The boolean lets the HTTP layer translate the
    outcome into a 204 vs a 404 -- it intentionally does not raise so
    callers can compose this in retry-safe loops.
    """
    existing = await repository.get(subscription_id)
    if existing is None or not secrets.compare_digest(existing.secret_token, token):
        return False
    await repository.deactivate(subscription_id)
    return True


def build_discord_embed(
    subscription: AlertSubscription, conjunction: dict[str, object]
) -> dict[str, object]:
    """Render a Discord-compatible embed body for ``conjunction``.

    Discord webhooks accept the legacy ``content`` key plus an
    ``embeds`` array. We ship both: a short ``content`` summary so the
    notification is readable in clients that strip embeds, and a rich
    embed with the structured fields.
    """
    sat_a = f"{conjunction['sat_a_name']} ({conjunction['sat_a_norad_id']})"
    sat_b = f"{conjunction['sat_b_name']} ({conjunction['sat_b_norad_id']})"
    miss = float(conjunction["miss_distance_km"])
    rel_v = float(conjunction["relative_velocity_km_s"])
    prob = float(conjunction["probability"])
    tca = conjunction["tca"]
    tca_str = tca.isoformat() if isinstance(tca, datetime) else str(tca)
    summary = (
        f"Conjunction alert: {sat_a} <-> {sat_b} at {tca_str} "
        f"(miss {miss:.3f} km, threshold {subscription.miss_distance_km_threshold:.2f} km)"
    )
    embed: dict[str, object] = {
        "title": "Orbital conjunction alert",
        "description": summary,
        "fields": [
            {"name": "Satellite A", "value": sat_a, "inline": True},
            {"name": "Satellite B", "value": sat_b, "inline": True},
            {"name": "TCA (UTC)", "value": tca_str, "inline": False},
            {"name": "Miss distance (km)", "value": f"{miss:.3f}", "inline": True},
            {"name": "Relative velocity (km/s)", "value": f"{rel_v:.3f}", "inline": True},
            {"name": "Probability", "value": f"{prob:.3g}", "inline": True},
        ],
    }
    return {"content": summary, "embeds": [embed]}


async def notify_pending_alerts(
    now: datetime,
    repository: AlertSubscriptionRepository,
    source: ConjunctionAlertSource,
    notifier: AlertNotifier,
    horizon_days: float,
) -> int:
    """Iterate every active subscription and POST/email matching conjunctions.

    Returns the number of successful deliveries. The function is safe to
    call repeatedly: the per-(subscription, conjunction) delivery is
    deduplicated through :meth:`AlertSubscriptionRepository.has_been_notified`.
    """
    horizon = now + timedelta(days=horizon_days)
    delivered = 0
    for subscription in await repository.list_active():
        conjunctions = await source.upcoming_conjunctions_for_satellites(
            subscription.norad_ids,
            subscription.miss_distance_km_threshold,
            horizon,
        )
        for conjunction in conjunctions:
            cid = str(conjunction["id"])
            if await repository.has_been_notified(subscription.id, cid):
                continue
            payload = build_discord_embed(subscription, conjunction)
            subject = "Orbital conjunction alert"
            ok = await notifier.notify(
                subscription.email_or_webhook_url,
                subject,
                str(payload["content"]),
                payload,
            )
            if not ok:
                logger.warning(
                    "alert delivery failed",
                    extra={
                        "subscription_id": subscription.id,
                        "conjunction_id": cid,
                    },
                )
                continue
            await repository.record_notified(subscription.id, cid)
            await repository.mark_notified(subscription.id, now)
            delivered += 1
    return delivered
