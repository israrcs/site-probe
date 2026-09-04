from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent.parent  # server/


class Settings(BaseSettings):
    """Runtime configuration. Every field can be overridden with the
    SITEPROBE_ environment variable prefix (e.g. SITEPROBE_MAX_PAGES)."""

    runs_dir: Path = BASE_DIR / "runs"
    cors_origins: str = "*"

    # httpx link checking
    request_timeout_s: int = 15
    link_check_concurrency: int = 10
    link_check_cap: int = 30          # max external links checked per page

    # per-engine timeout on a single page
    engine_timeout_s: int = 90

    # vendored axe-core for accessibility scans
    axe_path: Path = (
        Path(__file__).resolve().parent.parent
        / "services" / "engines" / "vendor" / "axe.min.js"
    )

    model_config = SettingsConfigDict(env_prefix="SITEPROBE_")


settings = Settings()
settings.runs_dir.mkdir(parents=True, exist_ok=True)
