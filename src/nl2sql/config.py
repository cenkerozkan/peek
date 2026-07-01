"""Application settings: env-driven config and config-file resolution."""

from pathlib import Path
from typing import Optional

from platformdirs import user_config_dir
from pydantic_settings import BaseSettings, SettingsConfigDict

_REGISTRY_FILENAME = "databases.toml"


class AppConfig(BaseSettings):
    """Server-wide settings, overridable via ``NL2SQL_*`` env vars.

    Attributes:
        config_file: Explicit path to the connection-registry TOML file.
            When unset, :meth:`resolved_config_file` derives a
            platform-appropriate default.
        max_rows: Default row cap applied by ``run_sql``.
    """

    model_config = SettingsConfigDict(env_prefix="NL2SQL_", extra="ignore")

    config_file: Optional[Path] = None
    max_rows: int = 1000

    def resolved_config_file(self) -> Path:
        """Return the connection-registry file this config points at.

        Returns:
            ``self.config_file`` if explicitly set, otherwise the default
            ``databases.toml`` inside the platform's user config directory.
        """
        if self.config_file is not None:
            return self.config_file
        return Path(user_config_dir("nl2sql")) / _REGISTRY_FILENAME
