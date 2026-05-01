"""Cross-cutting helpers shared by the inbound HTTP adapter.

The Pydantic schemas in :mod:`oc.interface.schemas` describe the public
JSON contract. They live on the boundary so they can be imported by both
the FastAPI routers and the OpenAPI generators without dragging in
SQLAlchemy or sgp4.
"""
