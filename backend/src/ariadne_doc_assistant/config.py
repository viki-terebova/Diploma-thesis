from __future__ import annotations

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


REPO_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=REPO_ROOT / ".env",
        env_prefix="",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "Ariadne"
    host: str = Field(default="0.0.0.0", validation_alias="APP_HOST")
    port: int = Field(default=8000, validation_alias="APP_PORT")
    log_level: str = Field(default="INFO", validation_alias="APP_LOG_LEVEL")
    project_root: Path = Field(default=REPO_ROOT, validation_alias="APP_PROJECT_ROOT")
    database_url: str = Field(
        default="postgresql+psycopg://ariadne_user:ariadne_db_password@localhost:5433/ariadne_db",
        validation_alias="POSTGRES_DATABASE_URL",
    )
    output_dir: Path = Field(default=REPO_ROOT / "output" / "proposals", validation_alias="APP_OUTPUT_DIR")
    plugin_path: Path | None = Field(default=None, validation_alias="APP_PLUGIN_PATH")
    enable_integrated_connectors: bool = Field(default=False, validation_alias="APP_ENABLE_INTEGRATED_CONNECTORS")
    llm_provider: str = Field(default="dummy", validation_alias="APP_LLM_PROVIDER")


settings = Settings()
