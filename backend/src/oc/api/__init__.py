"""Backwards-compatibility shim. HTTP routers now live in :mod:`oc.infrastructure.http`."""

from oc.infrastructure.http import conjunctions, health, satellites, stats

__all__ = ["conjunctions", "health", "satellites", "stats"]
