"""Application settings: env-driven config and config-file resolution."""

from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict

_LOCAL_CONFIG = Path(".peek") / "databases.toml"


def resolve_config_path() -> Path:
    """Return the path to the databases.toml file the CLI should use.

    ``.peek/databases.toml`` relative to the current working directory.

    Returns:
        Path that exists, or the cwd-local default if nothing
        exists anywhere.
    """
    local_path = Path.cwd() / _LOCAL_CONFIG
    if local_path.exists():
        return local_path

    return local_path


class AppConfig(BaseSettings):
    """Server-wide settings, overridable via ``PEEK_*`` env vars.

    Attributes:
        config_file: Explicit path to the connection-registry TOML file.
            When unset, :meth:`resolved_config_file` derives a
            platform-appropriate default.
        max_rows: Default row cap applied by ``run_sql``.
    """

    model_config = SettingsConfigDict(env_prefix="PEEK_", extra="ignore")

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
        return Path(resolve_config_path())
