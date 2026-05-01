"""Infrastructure layer: concrete adapters that satisfy application ports.

Adapters are the only place where third-party drivers (SQLAlchemy,
FastAPI, sgp4, httpx, scipy, APScheduler) are imported. The composition
root in :mod:`oc.main` wires concrete adapters into the FastAPI
dependency-injection graph.
"""
