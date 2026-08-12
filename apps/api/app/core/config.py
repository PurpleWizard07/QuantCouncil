"""Application settings loaded from environment variables.

Canonical environment variable names (see project contract / .env.example):
APP_ENV, DATABASE_URL, API_HOST, API_PORT, CORS_ORIGINS, ANTHROPIC_API_KEY.

A repo-root ``.env`` file (if present) is loaded via python-dotenv before the
Settings object is constructed. Repo layout is::

    <repo_root>/apps/api/app/core/config.py

so the repo root sits four directory levels above this file; we search every
ancestor upward so the lookup keeps working even if nesting changes.
"""

from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def _load_repo_root_dotenv() -> None:
    """Search upward from this file and load the first .env found.

    Existing process environment variables always win (override=False).
    """
    for parent in Path(__file__).resolve().parents:
        candidate = parent / ".env"
        if candidate.is_file():
            load_dotenv(candidate, override=False)
            return


def find_repo_root() -> Path:
    """Best-effort resolution of the repo root by walking up from this file.

    The repo root is the first ancestor that has sibling ``data/`` and
    ``packages/`` directories (the same marker used by
    ``data_connectors.cache._default_cache_dir``). Falls back to a fixed
    offset (this file lives at ``<repo_root>/apps/api/app/core/config.py``,
    so the root is four levels above ``apps/``) if the marker isn't found.
    """
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "data").is_dir() and (parent / "packages").is_dir():
            return parent
    # apps/api/app/core/config.py -> ... -> <repo_root>
    return here.parents[4]


class Settings(BaseSettings):
    """Typed application settings.

    All fields map to environment variables case-insensitively; unknown
    variables are ignored so a shared repo-root .env can carry settings for
    other services (web, postgres) without breaking the API.
    """

    model_config = SettingsConfigDict(extra="ignore", case_sensitive=False)

    app_env: str = "development"
    database_url: str = (
        "postgresql+psycopg2://quant:quant@localhost:5432/quantcouncil"
    )
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    # Raw comma-separated origins string (env var CORS_ORIGINS); consumed via
    # the parsed ``cors_origins`` property below.
    cors_origins_raw: str = Field(
        default="http://localhost:3000",
        validation_alias="CORS_ORIGINS",
    )
    # Optional; used by the AI committee (Phase 6) onward. Never required for
    # the foundation phase.
    anthropic_api_key: str = ""

    # --- AI Committee (Phase 6) ---
    # Default provider used by POST /committee/evaluate when the request
    # omits "provider". Defaults to "mock" so the app and every test work
    # with zero LLM credentials and zero network access.
    agent_provider: str = Field(
        default="mock", validation_alias="QUANTCOUNCIL_AGENT_PROVIDER"
    )

    # --- Persistence (optional) ---
    # Root directory for persisted backtest artifacts (equity_curve.json /
    # trades.json, one subdirectory per run). Empty means "use the default",
    # ``<repo_root>/data/backtests`` (see ``backtests_dir_path``).
    backtests_dir: str = Field(default="", validation_alias="BACKTESTS_DIR")

    @property
    def cors_origins(self) -> list[str]:
        """CORS_ORIGINS parsed into a list, splitting on commas."""
        configured = [
            origin.strip()
            for origin in self.cors_origins_raw.split(",")
            if origin.strip()
        ]
        if self.app_env.lower() in {"dev", "development", "local"}:
            configured.extend(
                f"http://{host}:{port}"
                for host in ("localhost", "127.0.0.1")
                for port in range(3000, 3011)
            )
        return list(dict.fromkeys(configured))

    @property
    def backtests_dir_path(self) -> Path:
        """Resolved backtest-artifact root directory.

        Returns ``BACKTESTS_DIR`` when set (as given; a relative value is
        resolved against the repo root), otherwise
        ``<repo_root>/data/backtests``. The directory is NOT created here --
        the persistence layer creates per-run subdirectories on demand.
        """
        if self.backtests_dir.strip():
            configured = Path(self.backtests_dir)
            if configured.is_absolute():
                return configured
            return find_repo_root() / configured
        return find_repo_root() / "data" / "backtests"


@lru_cache
def get_settings() -> Settings:
    """Cached settings accessor. Loads the repo-root .env exactly once."""
    _load_repo_root_dotenv()
    return Settings()
