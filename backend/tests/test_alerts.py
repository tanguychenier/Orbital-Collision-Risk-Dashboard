"""Tests for the alert subsystem (subscription lifecycle + notify_pending_alerts)."""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime, timedelta
from typing import Any

import httpx
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from oc.application.use_cases.alerts import (
    SubscriptionRequest,
    build_discord_embed,
    notify_pending_alerts,
    subscribe_to_alerts,
)
from oc.domain.entities import AlertSubscription
from oc.infrastructure.notifications import HttpWebhookNotifier
from oc.infrastructure.persistence.alert_subscription_repository import (
    SQLAlchemyAlertSubscriptionRepository,
    SQLAlchemyConjunctionAlertSource,
)
from oc.models import TLE, Conjunction, Satellite

DISCORD_URL = "https://discord.com/api/webhooks/12345/abcdef"


async def _seed_satellites_and_conjunction(session: AsyncSession) -> str:
    """Insert two satellites, two TLEs and one matching conjunction. Returns the conj id."""
    now = datetime.now(UTC)
    session.add_all(
        [
            Satellite(
                norad_id=42001,
                name="OPERATOR-SAT",
                country="FR",
                object_type="PAYLOAD",
                launch_date=date(2024, 3, 1),
                is_active=True,
            ),
            Satellite(
                norad_id=42002,
                name="DEBRIS-X",
                country="??",
                object_type="DEBRIS",
                launch_date=date(2010, 1, 1),
                is_active=True,
            ),
        ]
    )
    await session.flush()
    tle_a = TLE(
        norad_id=42001,
        epoch=now - timedelta(hours=2),
        line1="1 42001U 24015A   24001.00000000  .00000000  00000-0  00000+0 0    01",
        line2="2 42001  51.6000   0.0000 0000000   0.0000   0.0000 15.00000000    02",
    )
    tle_b = TLE(
        norad_id=42002,
        epoch=now - timedelta(hours=1),
        line1="1 42002U 10001A   24001.00000000  .00000000  00000-0  00000+0 0    03",
        line2="2 42002  51.6000   0.0000 0000000   0.0000   0.0000 15.00000000    04",
    )
    session.add_all([tle_a, tle_b])
    await session.flush()
    conj_id = uuid.uuid4().hex
    session.add(
        Conjunction(
            id=conj_id,
            sat_a_norad_id=42001,
            sat_b_norad_id=42002,
            tle_a_id=tle_a.id,
            tle_b_id=tle_b.id,
            tca=now + timedelta(hours=12),
            miss_distance_km=1.5,
            relative_velocity_km_s=14.1,
            probability=0.4,
        )
    )
    await session.commit()
    return conj_id


@pytest.mark.asyncio
async def test_subscribe_returns_id_and_manage_url(client: AsyncClient) -> None:
    """``POST /api/alerts/subscriptions`` returns a 201, an id, and a manage URL with token."""
    response = await client.post(
        "/api/alerts/subscriptions",
        json={
            "email_or_webhook_url": DISCORD_URL,
            "norad_ids": [42001],
            "miss_distance_km_threshold": 5.0,
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert "id" in body
    assert body["manage_url"].startswith("http")
    assert f"/alerts/{body['id']}" in body["manage_url"]
    assert "token=" in body["manage_url"]


@pytest.mark.asyncio
async def test_bad_webhook_url_rejected_with_422(client: AsyncClient) -> None:
    """A target that is neither a URL nor an email yields 422."""
    response = await client.post(
        "/api/alerts/subscriptions",
        json={
            "email_or_webhook_url": "not a url",
            "norad_ids": [42001],
            "miss_distance_km_threshold": 5.0,
        },
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_get_subscription_requires_correct_token(client: AsyncClient) -> None:
    """``GET`` returns the subscription when the token matches; 404 otherwise."""
    create = await client.post(
        "/api/alerts/subscriptions",
        json={
            "email_or_webhook_url": "ops@example.com",
            "norad_ids": [42001],
            "miss_distance_km_threshold": 2.5,
        },
    )
    assert create.status_code == 201
    body = create.json()
    sub_id = body["id"]
    manage_url = body["manage_url"]
    token = manage_url.split("token=", 1)[1]

    ok = await client.get(f"/api/alerts/subscriptions/{sub_id}", params={"token": token})
    assert ok.status_code == 200
    detail = ok.json()
    assert detail["id"] == sub_id
    assert detail["norad_ids"] == [42001]
    assert detail["is_active"] is True

    bad = await client.get(f"/api/alerts/subscriptions/{sub_id}", params={"token": "wrong"})
    assert bad.status_code == 404


@pytest.mark.asyncio
async def test_unsubscribe_with_wrong_token_returns_404(client: AsyncClient) -> None:
    """``DELETE`` with a wrong token yields 404 and does NOT deactivate the row."""
    create = await client.post(
        "/api/alerts/subscriptions",
        json={
            "email_or_webhook_url": DISCORD_URL,
            "norad_ids": [42001],
            "miss_distance_km_threshold": 5.0,
        },
    )
    body = create.json()
    sub_id = body["id"]
    token = body["manage_url"].split("token=", 1)[1]

    bad = await client.delete(f"/api/alerts/subscriptions/{sub_id}", params={"token": "nope"})
    assert bad.status_code == 404

    # Confirm the row is still active.
    ok = await client.get(f"/api/alerts/subscriptions/{sub_id}", params={"token": token})
    assert ok.status_code == 200
    assert ok.json()["is_active"] is True


@pytest.mark.asyncio
async def test_unsubscribe_with_correct_token_returns_204(client: AsyncClient) -> None:
    """``DELETE`` with the correct token returns 204 and the row is no longer active."""
    create = await client.post(
        "/api/alerts/subscriptions",
        json={
            "email_or_webhook_url": "ops@example.com",
            "norad_ids": [42001],
            "miss_distance_km_threshold": 5.0,
        },
    )
    body = create.json()
    sub_id = body["id"]
    token = body["manage_url"].split("token=", 1)[1]

    deleted = await client.delete(f"/api/alerts/subscriptions/{sub_id}", params={"token": token})
    assert deleted.status_code == 204

    after = await client.get(f"/api/alerts/subscriptions/{sub_id}", params={"token": token})
    assert after.status_code == 200
    assert after.json()["is_active"] is False


def test_build_discord_embed_shape() -> None:
    """The Discord payload must carry both ``content`` and ``embeds[0]`` with the key fields."""
    subscription = AlertSubscription(
        id="abc",
        email_or_webhook_url=DISCORD_URL,
        norad_ids=(42001,),
        miss_distance_km_threshold=5.0,
        created_at=datetime.now(UTC),
        secret_token="t",
    )
    conjunction = {
        "id": "c1",
        "sat_a_norad_id": 42001,
        "sat_a_name": "OPERATOR-SAT",
        "sat_b_norad_id": 42002,
        "sat_b_name": "DEBRIS-X",
        "tca": datetime(2026, 5, 1, 12, 0, tzinfo=UTC),
        "miss_distance_km": 1.5,
        "relative_velocity_km_s": 14.1,
        "probability": 0.4,
    }
    payload = build_discord_embed(subscription, conjunction)
    assert "content" in payload
    embeds = payload["embeds"]
    assert isinstance(embeds, list) and len(embeds) == 1
    embed = embeds[0]
    assert isinstance(embed, dict)
    assert embed["title"] == "Orbital conjunction alert"
    fields = embed["fields"]
    assert isinstance(fields, list)
    names = {f["name"] for f in fields if isinstance(f, dict)}
    assert "Satellite A" in names
    assert "Satellite B" in names
    assert "Miss distance (km)" in names


class _RecordingTransport(httpx.AsyncBaseTransport):
    """Captures POST bodies so we can assert on the Discord embed shape."""

    def __init__(self) -> None:
        self.requests: list[dict[str, Any]] = []

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        body: dict[str, Any] = {}
        if request.content:
            import json as _json

            body = _json.loads(request.content.decode("utf-8"))
        self.requests.append({"url": str(request.url), "body": body})
        return httpx.Response(200, json={"ok": True})


@pytest.mark.asyncio
async def test_notify_pending_alerts_posts_discord_payload(db_session: AsyncSession) -> None:
    """``notify_pending_alerts`` posts a Discord-shaped JSON to the subscriber's webhook."""
    conj_id = await _seed_satellites_and_conjunction(db_session)

    repository = SQLAlchemyAlertSubscriptionRepository(db_session)
    source = SQLAlchemyConjunctionAlertSource(db_session)
    transport = _RecordingTransport()
    async with httpx.AsyncClient(transport=transport) as http_client:
        notifier = HttpWebhookNotifier(client=http_client)
        await subscribe_to_alerts(
            SubscriptionRequest(
                email_or_webhook_url=DISCORD_URL,
                norad_ids=(42001,),
                miss_distance_km_threshold=5.0,
            ),
            repository,
            "https://app.example.com",
            datetime.now(UTC),
        )
        await db_session.commit()

        delivered = await notify_pending_alerts(
            now=datetime.now(UTC),
            repository=repository,
            source=source,
            notifier=notifier,
            horizon_days=7.0,
        )

    assert delivered == 1
    assert len(transport.requests) == 1
    request = transport.requests[0]
    assert request["url"] == DISCORD_URL
    body = request["body"]
    assert "content" in body
    assert isinstance(body["embeds"], list) and len(body["embeds"]) == 1
    embed = body["embeds"][0]
    assert embed["title"] == "Orbital conjunction alert"
    field_names = {f["name"] for f in embed["fields"]}
    assert "Miss distance (km)" in field_names

    # Idempotency: re-running the loop must not re-post the same conjunction.
    transport.requests.clear()
    async with httpx.AsyncClient(transport=transport) as http_client:
        notifier = HttpWebhookNotifier(client=http_client)
        delivered = await notify_pending_alerts(
            now=datetime.now(UTC),
            repository=repository,
            source=source,
            notifier=notifier,
            horizon_days=7.0,
        )
    assert delivered == 0
    assert transport.requests == []
    # Reference the seeded id so static analysis sees the value as used.
    assert isinstance(conj_id, str) and len(conj_id) == 32
