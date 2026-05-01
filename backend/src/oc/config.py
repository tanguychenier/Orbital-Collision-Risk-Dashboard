"""Application configuration loaded from environment variables."""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Top-level configuration object.

    Values can be overridden by environment variables (prefix ``OC_``) or by a
    ``.env`` file at the project root.
    """

    model_config = SettingsConfigDict(
        env_prefix="OC_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "orbital-conjunctions"
    version: str = "0.1.0"
    environment: str = "dev"

    # Database. Defaults to a local SQLite file so the app can run with no setup.
    database_url: str = "sqlite+aiosqlite:///./orbital_conjunctions.db"

    # CelesTrak fetch.
    celestrak_url: str = "https://celestrak.org/NORAD/elements/gp.php?GROUP=active&FORMAT=tle"
    celestrak_starlink_url: str = (
        "https://celestrak.org/NORAD/elements/gp.php?GROUP=starlink&FORMAT=tle"
    )
    http_timeout_seconds: float = 30.0

    # Conjunction screening parameters.
    screening_horizon_hours: float = 72.0
    screening_coarse_step_seconds: float = 60.0
    screening_fine_step_seconds: float = 1.0
    screening_perigee_apogee_buffer_km: float = 50.0
    screening_distance_threshold_km: float = 50.0
    screening_max_pairs: int = Field(
        default=20_000,
        description="Hard limit on number of pairs evaluated per recompute.",
    )

    # Probability model (placeholder).
    probability_sigma_km: float = 1.0

    # Schedule cadences.
    tle_refresh_interval_hours: float = 4.0
    conjunction_refresh_interval_minutes: float = 30.0

    # API.
    cors_origins: list[str] = Field(default_factory=lambda: ["*"])
    api_default_limit: int = 200
    api_max_limit: int = 1000
    public_base_url: str = Field(
        default="https://orbital-conjunctions.example.com",
        description=(
            "Origin used to construct deep-links emitted by the API "
            "(iCalendar URL property, manage URLs, ...). Override per "
            "deployment."
        ),
    )

    # Whether the FastAPI lifespan should boot the APScheduler worker.
    enable_scheduler: bool = False

    # Alert subsystem.
    alerts_base_url: str = "http://localhost:8000"
    alerts_horizon_days: float = 7.0
    alerts_notify_interval_minutes: float = 15.0
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_username: str | None = None
    smtp_password: str | None = None
    smtp_from_address: str = "alerts@orbital-conjunctions.local"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached :class:`Settings` instance."""
    return Settings()
