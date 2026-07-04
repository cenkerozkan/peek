"""Reads the user-maintained alias -> connection-string registry file.

The registry is a TOML file shaped like::

    [databases.psql]
    url = "postgresql+psycopg://user:pw@host:5432/db"
    dialect = "postgres"

Only the file *path* ever appears in error messages here — never its
contents, since that would leak connection strings to a caller.
"""

from pathlib import Path
from typing import Dict

from pydantic import ValidationError
from pydantic_settings import (
    BaseSettings,
    SettingsConfigDict,
    TomlConfigSettingsSource,
)

from src.peek.errors import ConfigError
from src.peek.models.config import DatabaseEntry


def load_registry(path: Path) -> Dict[str, DatabaseEntry]:
    """Load and validate the connection registry at ``path``.

    Args:
        path: Location of the ``databases.toml`` registry file.

    Returns:
        A mapping of alias to :class:`DatabaseEntry`.

    Raises:
        ConfigError: If the file is missing, malformed, fails validation,
            or declares no databases.
    """
    if not path.is_file():
        raise ConfigError(f"No config file found at: {path}")

    class _RegistryFile(BaseSettings):
        model_config = SettingsConfigDict(extra="forbid", toml_file=path)

        databases: Dict[str, DatabaseEntry] = {}

        @classmethod
        def settings_customise_sources(
            cls,
            settings_cls,
            init_settings,
            env_settings,
            dotenv_settings,
            file_secret_settings,
        ):
            return (TomlConfigSettingsSource(settings_cls),)

    try:
        registry = _RegistryFile()
    except ValidationError as error:
        raise ConfigError(f"Config file is invalid: {path}") from error
    except Exception as error:
        raise ConfigError(f"Could not read config file: {path}") from error

    if not registry.databases:
        raise ConfigError(f"Config file declares no databases: {path}")

    return registry.databases
