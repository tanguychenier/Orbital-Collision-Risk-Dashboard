"""Pure value objects used across the domain layer.

Value objects are immutable, equality-by-content data containers. They
have no behaviour beyond simple validation in ``__post_init__``.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

import numpy as np


@dataclass(frozen=True)
class StateVector:
    """A position/velocity pair in the TEME frame.

    Attributes:
        position_km: Length-3 array, kilometers.
        velocity_km_s: Length-3 array, kilometers per second.
    """

    position_km: np.ndarray
    velocity_km_s: np.ndarray

    def __post_init__(self) -> None:
        if self.position_km.shape != (3,):
            raise ValueError("position_km must have shape (3,)")
        if self.velocity_km_s.shape != (3,):
            raise ValueError("velocity_km_s must have shape (3,)")


@dataclass(frozen=True)
class Ephemeris:
    """A propagated trajectory expressed as parallel time/position/velocity arrays.

    Attributes:
        times: UTC sample times of length ``N``.
        positions: ``(N, 3)`` array of position vectors (km, TEME frame).
        velocities: ``(N, 3)`` array of velocity vectors (km/s, TEME frame).
    """

    times: tuple[datetime, ...]
    positions: np.ndarray
    velocities: np.ndarray

    def __post_init__(self) -> None:
        n = len(self.times)
        if self.positions.shape != (n, 3):
            raise ValueError("positions shape mismatch")
        if self.velocities.shape != (n, 3):
            raise ValueError("velocities shape mismatch")


@dataclass(frozen=True)
class OrbitalElements:
    """Gross orbital geometry derived from a SGP4 record.

    Attributes:
        semi_major_axis_km: Semi-major axis in kilometers.
        perigee_altitude_km: Altitude above Earth's mean radius at perigee.
        apogee_altitude_km: Altitude above Earth's mean radius at apogee.
    """

    semi_major_axis_km: float
    perigee_altitude_km: float
    apogee_altitude_km: float


@dataclass(frozen=True)
class CandidateInterval:
    """A coarse time window where two satellites came within the screening threshold.

    Indices reference the shared time grid that produced the interval.
    """

    start_index: int
    end_index: int
    start_time: datetime
    end_time: datetime
    min_distance_km: float
