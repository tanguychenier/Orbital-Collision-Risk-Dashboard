"""Backwards-compatibility shim package.

Domain services were promoted to ``oc.application.use_cases`` and the
adapters in :mod:`oc.infrastructure`. The submodules in this package
re-export the original public surface so legacy imports keep working.
"""
