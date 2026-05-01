"""``/api/calendar.ics`` -- iCalendar feed of upcoming conjunctions.

The feed is meant to be subscribed to by satellite operators from
their everyday calendar app (Google Calendar, Outlook, Apple Calendar)
so close approaches show up alongside their meetings without polling
the dashboard. The query parameters filter the feed by satellite,
horizon, and miss-distance threshold so a single subscription can be
narrowed to a specific operator's fleet.

The output strictly follows RFC 5545: lines end with CRLF, every line
longer than 75 octets is folded with CRLF + space, and reserved
characters in DESCRIPTION / SUMMARY are escaped per section 3.3.11.
"""

from __future__ import annotations

from collections.abc import Iterable
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from oc.config import Settings, get_settings
from oc.db import get_db_session
from oc.infrastructure.persistence.models import Conjunction

# An iCal VEVENT spans a duration; conjunctions are essentially
# instantaneous. We render them as a 60-second window centred on the
# TCA so calendar UIs do not collapse them to "all-day" placeholders.
_EVENT_DURATION = timedelta(seconds=60)
_DEFAULT_HORIZON_HOURS: float = 7.0 * 24.0
_MAX_HORIZON_HOURS: float = 30.0 * 24.0
_DEFAULT_MAX_DISTANCE_KM: float = 5.0

router = APIRouter()


def _ensure_utc(dt: datetime) -> datetime:
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=UTC)


def _fmt_ical_dt(dt: datetime) -> str:
    """Format ``dt`` as ``YYYYMMDDTHHMMSSZ`` (UTC, RFC 5545 form)."""
    return _ensure_utc(dt).astimezone(UTC).strftime("%Y%m%dT%H%M%SZ")


def _escape_text(value: str) -> str:
    """Escape RFC 5545 reserved characters in a TEXT property."""
    return (
        value.replace("\\", "\\\\")
        .replace(";", "\\;")
        .replace(",", "\\,")
        .replace("\r\n", "\\n")
        .replace("\n", "\\n")
    )


def _fold(line: str) -> str:
    """Fold a content line at the 75-octet boundary per RFC 5545."""
    encoded = line.encode("utf-8")
    if len(encoded) <= 75:
        return line
    chunks: list[bytes] = []
    cursor = 0
    while cursor < len(encoded):
        chunk = encoded[cursor : cursor + 75]
        # Avoid splitting a multi-byte UTF-8 sequence: trim back to a
        # safe boundary if the last byte is a continuation byte.
        while chunk and (chunk[-1] & 0xC0) == 0x80 and len(chunk) > 1:
            chunk = chunk[:-1]
        chunks.append(chunk)
        cursor += len(chunk)
    return "\r\n ".join(c.decode("utf-8") for c in chunks)


def _calendar_lines(
    rows: Iterable[Conjunction],
    base_url: str,
    feed_name: str,
) -> Iterable[str]:
    """Yield the raw iCalendar content lines for ``rows``."""
    yield "BEGIN:VCALENDAR"
    yield "VERSION:2.0"
    yield "PRODID:-//Tan-Software//Orbital Conjunctions//EN"
    yield "CALSCALE:GREGORIAN"
    yield "METHOD:PUBLISH"
    yield _fold(f"X-WR-CALNAME:{_escape_text(feed_name)}")
    now_stamp = _fmt_ical_dt(datetime.now(UTC))

    for c in rows:
        tca = _ensure_utc(c.tca)
        sat_a = c.sat_a.name
        sat_b = c.sat_b.name
        miss = c.miss_distance_km
        velocity = c.relative_velocity_km_s
        prob = c.probability
        summary = f"Conjunction: {sat_a} ↔ {sat_b} ({miss:.2f} km)"
        description = (
            f"Miss distance: {miss:.3f} km. "
            f"Relative velocity: {velocity:.2f} km/s. "
            f"Probability of collision: {prob:.2e}."
        )
        url = f"{base_url.rstrip('/')}/?conjunction={c.id}"
        yield "BEGIN:VEVENT"
        yield _fold(f"UID:{c.id}@orbital-conjunctions")
        yield f"DTSTAMP:{now_stamp}"
        yield f"DTSTART:{_fmt_ical_dt(tca)}"
        yield f"DTEND:{_fmt_ical_dt(tca + _EVENT_DURATION)}"
        yield _fold(f"SUMMARY:{_escape_text(summary)}")
        yield _fold(f"DESCRIPTION:{_escape_text(description)}")
        yield _fold(f"URL:{url}")
        yield "END:VEVENT"

    yield "END:VCALENDAR"


@router.get(
    "/calendar.ics",
    responses={200: {"content": {"text/calendar": {}}}},
)
async def calendar_feed(
    norad_id: list[int] | None = Query(
        default=None,
        description=(
            "Optional NORAD catalog id(s). When provided, only conjunctions "
            "involving one of these satellites are emitted."
        ),
    ),
    hours: float = Query(default=_DEFAULT_HORIZON_HOURS, gt=0.0, le=_MAX_HORIZON_HOURS),
    max_distance_km: float = Query(default=_DEFAULT_MAX_DISTANCE_KM, gt=0.0, le=1000.0),
    session: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
) -> Response:
    """Return an iCalendar feed of upcoming conjunctions.

    Designed to be subscribed to by an external calendar client. The
    payload is ``Content-Type: text/calendar; charset=utf-8`` per
    RFC 5545; CRLF line endings and folded long lines are honoured.
    """
    now = datetime.now(UTC)
    horizon = now + timedelta(hours=hours)
    stmt = (
        select(Conjunction)
        .options(selectinload(Conjunction.sat_a), selectinload(Conjunction.sat_b))
        .where(
            Conjunction.tca >= now,
            Conjunction.tca <= horizon,
            Conjunction.miss_distance_km <= max_distance_km,
        )
        .order_by(Conjunction.tca)
        .limit(min(1000, settings.api_max_limit))
    )
    if norad_id:
        stmt = stmt.where(
            or_(
                Conjunction.sat_a_norad_id.in_(norad_id),
                Conjunction.sat_b_norad_id.in_(norad_id),
            )
        )
    rows = (await session.execute(stmt)).scalars().all()

    feed_name = (
        f"Orbital conjunctions for {','.join(str(i) for i in norad_id)}"
        if norad_id
        else "Orbital conjunctions"
    )
    body = "\r\n".join(_calendar_lines(rows, settings.public_base_url, feed_name)) + "\r\n"
    return Response(
        content=body,
        media_type="text/calendar; charset=utf-8",
        headers={
            "Content-Disposition": 'inline; filename="orbital-conjunctions.ics"',
            "Cache-Control": "public, max-age=300",
        },
    )
