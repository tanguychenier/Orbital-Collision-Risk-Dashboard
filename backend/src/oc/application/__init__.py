"""Application layer: use cases orchestrate the domain through ports.

This package depends only on :mod:`oc.domain` and the ``Protocol`` types
declared in :mod:`oc.application.ports`. It must not import SQLAlchemy,
FastAPI, sgp4, httpx, scipy, or any other adapter-level dependency.
"""
