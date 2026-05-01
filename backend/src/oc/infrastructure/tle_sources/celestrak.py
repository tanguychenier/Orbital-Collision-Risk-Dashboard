"""HTTP adapter for the CelesTrak TLE source.

Implements the :class:`oc.application.ports.TLESource` port. The same
adapter handles every CelesTrak group (``active``, ``starlink``, ...)
since the URL is supplied per call. Swap in a Space-Track adapter by
implementing the same protocol.
"""

from __future__ import annotations

import httpx


class CelestrakTLESource:
    """Fetch TLE text over HTTP. Honours an optional injected client for tests."""

    def __init__(
        self,
        client: httpx.AsyncClient | None = None,
        timeout_seconds: float = 30.0,
    ) -> None:
        self._client = client
        self._timeout_seconds = timeout_seconds

    async def fetch(self, url: str) -> str:
        """Fetch ``url`` and return the raw response body as text."""
        if self._client is not None:
            return await _do_fetch(self._client, url)
        async with httpx.AsyncClient(timeout=self._timeout_seconds) as client:
            return await _do_fetch(client, url)


async def _do_fetch(client: httpx.AsyncClient, url: str) -> str:
    """Issue the GET, raise for status, and return the response body."""
    response = await client.get(url)
    response.raise_for_status()
    return response.text


async def fetch_tle_text(
    url: str,
    *,
    client: httpx.AsyncClient | None = None,
    timeout: float = 30.0,  # noqa: ASYNC109 -- forwarded to httpx.AsyncClient, not asyncio
) -> str:
    """Module-level convenience wrapper preserved for backwards compatibility."""
    source = CelestrakTLESource(client=client, timeout_seconds=timeout)
    return await source.fetch(url)
