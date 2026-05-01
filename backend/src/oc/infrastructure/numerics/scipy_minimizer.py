"""Scipy-backed bounded scalar minimizer adapter."""

from __future__ import annotations

from collections.abc import Callable

from scipy.optimize import minimize_scalar


class ScipyBoundedMinimizer:
    """:class:`oc.application.ports.BoundedScalarMinimizer` backed by scipy."""

    def minimize(
        self,
        objective: Callable[[float], float],
        lower: float,
        upper: float,
        tolerance: float,
    ) -> float:
        """Return the ``x`` minimising ``objective`` on ``[lower, upper]``."""
        result = minimize_scalar(
            objective,
            bounds=(lower, upper),
            method="bounded",
            options={"xatol": tolerance},
        )
        return float(result.x)
