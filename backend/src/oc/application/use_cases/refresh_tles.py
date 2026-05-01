"""TLE ingestion use case.

Pulls a CelesTrak-style 3-line TLE feed, parses it, and persists the
result through the :class:`oc.application.ports.TLERepository` port.
The persistence step is idempotent: an unchanged TLE (same ``epoch`` for
the same ``norad_id``) is a no-op.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta

from oc.application.ports import TLERepository, TLESource
from oc.domain.entities import ParsedTLE

logger = logging.getLogger(__name__)

# --- TLE format constants ----------------------------------------------------
# Two-digit year split convention used by CelesTrak / Spacetrack: years
# 57-99 belong to the 1900s (Sputnik 1 launched in 1957), 00-56 to the
# 2000s.
_TWO_DIGIT_YEAR_SPLIT: int = 57
_LINE1_LENGTH_TO_PARSE_NORAD: int = 7
_LINE1_LENGTH_TO_PARSE_EPOCH: int = 32
_LINE1_NORAD_SLICE = slice(2, 7)
_LINE1_EPOCH_YEAR_SLICE = slice(18, 20)
_LINE1_EPOCH_DAY_SLICE = slice(20, 32)


class TLEParseError(ValueError):
    """Raised when a TLE block fails parsing or validation."""


def _parse_norad_id(line1: str) -> int:
    """Extract the NORAD catalog id from a TLE line 1."""
    if len(line1) < _LINE1_LENGTH_TO_PARSE_NORAD or not line1.startswith("1 "):
        raise TLEParseError(f"line1 missing NORAD field: {line1!r}")
    raw = line1[_LINE1_NORAD_SLICE].strip()
    if not raw.isdigit():
        raise TLEParseError(f"NORAD id not numeric: {raw!r}")
    return int(raw)


def _parse_epoch(line1: str) -> datetime:
    """Extract the epoch (UTC) encoded in TLE line 1.

    The TLE epoch is two-digit year + day of year (with fractional day).
    """
    if len(line1) < _LINE1_LENGTH_TO_PARSE_EPOCH:
        raise TLEParseError(f"line1 too short for epoch: {line1!r}")
    yr_raw = line1[_LINE1_EPOCH_YEAR_SLICE]
    day_raw = line1[_LINE1_EPOCH_DAY_SLICE]
    try:
        yr = int(yr_raw)
        day = float(day_raw)
    except ValueError as exc:
        raise TLEParseError(f"unable to parse epoch fields: {line1!r}") from exc
    year = 1900 + yr if yr >= _TWO_DIGIT_YEAR_SPLIT else 2000 + yr
    base = datetime(year, 1, 1, tzinfo=UTC)
    return base + timedelta(days=day - 1.0)


def parse_tle_text(text: str) -> list[ParsedTLE]:
    """Parse CelesTrak's standard 3-line TLE text.

    Each satellite is represented by three consecutive lines: a name
    line, a line starting with ``1 ``, and a line starting with ``2 ``.

    Lines are normalised: trailing whitespace is stripped and blank lines
    are skipped. Malformed blocks are skipped with a logged warning
    rather than aborting the whole batch.
    """
    lines = [line.rstrip() for line in text.splitlines() if line.strip()]
    parsed: list[ParsedTLE] = []
    i = 0
    while i + 2 < len(lines) + 1:
        if i + 2 >= len(lines):
            break
        name_line = lines[i]
        line1 = lines[i + 1]
        line2 = lines[i + 2]
        if not line1.startswith("1 ") or not line2.startswith("2 "):
            logger.warning(
                "skipping malformed TLE block", extra={"index": i, "satellite": name_line}
            )
            i += 1
            continue
        try:
            norad_id = _parse_norad_id(line1)
            epoch = _parse_epoch(line1)
        except TLEParseError as exc:
            logger.warning("TLE parse error", extra={"error": str(exc), "satellite": name_line})
            i += 3
            continue
        parsed.append(
            ParsedTLE(
                name=name_line.strip(),
                norad_id=norad_id,
                line1=line1,
                line2=line2,
                epoch=epoch,
            )
        )
        i += 3
    return parsed


async def refresh_tles_from_url(
    source: TLESource,
    repository: TLERepository,
    url: str,
) -> tuple[int, int, int]:
    """Fetch ``url``, parse the TLE catalog, and persist the result.

    Args:
        source: Adapter implementing :class:`oc.application.ports.TLESource`.
        repository: Adapter implementing
            :class:`oc.application.ports.TLERepository`.
        url: HTTP endpoint serving the TLE text.

    Returns:
        ``(parsed_count, satellites_upserted, tles_inserted)``.
    """
    text = await source.fetch(url)
    parsed = parse_tle_text(text)
    sats, tles = await repository.upsert_parsed_tles(parsed)
    logger.info(
        "tle ingestion complete",
        extra={"url": url, "parsed": len(parsed), "new_satellites": sats, "new_tles": tles},
    )
    return len(parsed), sats, tles
