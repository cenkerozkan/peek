"""Reads the user-maintained alias -> connection-string registry file.

The registry is a TOML file shaped like::

    [databases.psql]
    url = "postgresql+psycopg://user:pw@host:5432/db"
    dialect = "postgres"

Only the file *path* ever appears in error messages here — never its
contents, since that would leak connection strings to a caller.
"""

from pathlib import Path
from typing import Any, Dict

import tomlkit
from pydantic import ValidationError
from pydantic_settings import (
    BaseSettings,
    SettingsConfigDict,
    TomlConfigSettingsSource,
)

from peek.errors import ConfigError
from peek.models.config import DatabaseEntry


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


def _entry_to_dict(entry: DatabaseEntry) -> Dict[str, Any]:
    """Convert a DatabaseEntry to a plain dict for TOML serialization.

    Omits ``dialect`` and ``exclude_tables`` when they hold default values.
    """
    result: Dict[str, Any] = {"url": entry.url.get_secret_value()}
    if entry.dialect is not None:
        result["dialect"] = entry.dialect
    if entry.exclude_tables:
        result["exclude_tables"] = entry.exclude_tables
    return result


def save_entry(path: Path, alias: str, entry: DatabaseEntry) -> None:
    """Persist a single database entry to the registry file.

    If the file already exists the operation preserves comments and
    formatting; otherwise a new document is created with a
    ``[databases]`` table.

    Args:
        path: Location of the ``databases.toml`` registry file.
        alias: The database alias (key under ``[databases]``).
        entry: The entry to write.

    Raises:
        ConfigError: If the existing file cannot be parsed.
    """
    doc: Any
    if path.is_file():
        try:
            with open(path, "rb") as f:
                doc = tomlkit.load(f)
        except Exception as error:
            raise ConfigError(f"Could not read config file: {path}") from error
    else:
        doc = tomlkit.document()

    if "databases" not in doc:
        databases = tomlkit.table()
        doc.add("databases", databases)

    doc["databases"][alias] = _entry_to_dict(entry)

    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, "w") as f:
        tomlkit.dump(doc, f)


def remove_entry(path: Path, alias: str) -> None:
    """Remove a database entry from the registry file.

    Args:
        path: Location of the ``databases.toml`` registry file.
        alias: The database alias to remove.

    Raises:
        ConfigError: If the file is missing or the alias is not found.
    """
    if not path.is_file():
        raise ConfigError(f"No config file found at: {path}")

    with open(path, "rb") as f:
        doc = tomlkit.load(f)

    databases = doc.get("databases")
    if databases is None or alias not in databases:
        raise ConfigError(f"No database with alias '{alias}' in {path}")

    del databases[alias]

    with open(path, "w") as f:
        tomlkit.dump(doc, f)
