"""``/api/alerts`` endpoints for the alert subscription subsystem."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from oc.application.use_cases.alerts import (
    AlertValidationError,
    SubscriptionRequest,
    subscribe_to_alerts,
    unsubscribe_from_alerts,
)
from oc.config import Settings, get_settings
from oc.db import get_db_session
from oc.domain.entities import AlertSubscription
from oc.infrastructure.persistence.alert_subscription_repository import (
    SQLAlchemyAlertSubscriptionRepository,
)
from oc.interface.schemas import (
    AlertSubscriptionCreate,
    AlertSubscriptionCreated,
    AlertSubscriptionPublic,
)

router = APIRouter()


def _to_public(subscription: AlertSubscription) -> AlertSubscriptionPublic:
    """Render a subscription without exposing the secret token."""
    return AlertSubscriptionPublic(
        id=subscription.id,
        email_or_webhook_url=subscription.email_or_webhook_url,
        norad_ids=list(subscription.norad_ids),
        miss_distance_km_threshold=subscription.miss_distance_km_threshold,
        is_active=subscription.is_active,
        created_at=subscription.created_at,
        last_notified_at=subscription.last_notified_at,
    )


@router.post(
    "/alerts/subscriptions",
    response_model=AlertSubscriptionCreated,
    status_code=status.HTTP_201_CREATED,
)
async def create_subscription(
    payload: AlertSubscriptionCreate,
    session: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
) -> AlertSubscriptionCreated:
    """Create a new alert subscription and return its manage URL."""
    repository = SQLAlchemyAlertSubscriptionRepository(session)
    try:
        request = SubscriptionRequest(
            email_or_webhook_url=payload.email_or_webhook_url,
            norad_ids=tuple(payload.norad_ids),
            miss_distance_km_threshold=payload.miss_distance_km_threshold,
        )
    except (ValueError, ValidationError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc
    try:
        result = await subscribe_to_alerts(
            request,
            repository,
            settings.alerts_base_url,
            datetime.now(UTC),
        )
    except AlertValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc
    await session.commit()
    return AlertSubscriptionCreated(id=result.subscription.id, manage_url=result.manage_url)


@router.get(
    "/alerts/subscriptions/{subscription_id}",
    response_model=AlertSubscriptionPublic,
)
async def get_subscription(
    subscription_id: str,
    token: str = Query(..., description="Secret token returned at creation time."),
    session: AsyncSession = Depends(get_db_session),
) -> AlertSubscriptionPublic:
    """Return one subscription if ``token`` matches, otherwise 404."""
    repository = SQLAlchemyAlertSubscriptionRepository(session)
    sub = await repository.get(subscription_id)
    if sub is None or sub.secret_token != token:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="subscription not found")
    return _to_public(sub)


@router.delete(
    "/alerts/subscriptions/{subscription_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_subscription(
    subscription_id: str,
    token: str = Query(..., description="Secret token returned at creation time."),
    session: AsyncSession = Depends(get_db_session),
) -> None:
    """Soft-delete a subscription, returning 204 on success or 404 if the token mismatches."""
    repository = SQLAlchemyAlertSubscriptionRepository(session)
    deactivated = await unsubscribe_from_alerts(subscription_id, token, repository)
    if not deactivated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="subscription not found")
    await session.commit()
