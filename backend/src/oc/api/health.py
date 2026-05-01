"""Backwards-compatibility shim. See :mod:`oc.infrastructure.http.health`."""

from oc.infrastructure.http.health import health, router

__all__ = ["health", "router"]
