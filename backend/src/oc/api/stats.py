"""Backwards-compatibility shim. See :mod:`oc.infrastructure.http.stats`."""

from oc.infrastructure.http.stats import router, stats

__all__ = ["router", "stats"]
