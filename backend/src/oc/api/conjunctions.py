"""Backwards-compatibility shim. See :mod:`oc.infrastructure.http.conjunctions`."""

from oc.infrastructure.http.conjunctions import get_conjunction, list_conjunctions, router

__all__ = ["get_conjunction", "list_conjunctions", "router"]
