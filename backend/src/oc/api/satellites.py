"""Backwards-compatibility shim. See :mod:`oc.infrastructure.http.satellites`."""

from oc.infrastructure.http.satellites import list_satellites, router

__all__ = ["list_satellites", "router"]
