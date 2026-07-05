"""Tests for the connection registry service."""

from pathlib import Path

import pytest
from sqlalchemy import text

from src.peek.config import AppConfig
from src.peek.errors import RegistryError
from src.peek.services.connection_registry import ConnectionRegistry


def _write_registry(tmp_path: Path, content: str) -> Path:
    path = tmp_path / "databases.toml"
    path.write_text(content)
    return path


@pytest.fixture
def registry(tmp_path: Path) -> ConnectionRegistry:
    path = _write_registry(
        tmp_path,
        """
        [databases.main]
        url = "sqlite://"

        [databases.reporting]
        url = "sqlite://"
        dialect = "sqlite"
        """,
    )
    config = AppConfig(config_file=path)
    return ConnectionRegistry.from_config(config)


def test_aliases_lists_every_registered_database(
    registry: ConnectionRegistry,
) -> None:
    """aliases() reflects every entry in the config file."""
    assert set(registry.aliases()) == {"main", "reporting"}


def test_get_engine_returns_a_working_engine(
    registry: ConnectionRegistry,
) -> None:
    """The returned engine can open a connection."""
    engine = registry.get_engine("main")

    with engine.connect() as connection:
        result = connection.execute(text("SELECT 1")).scalar()
    assert result == 1
    assert engine.dialect.name == "sqlite"


def test_get_engine_unknown_alias_raises_registry_error(
    registry: ConnectionRegistry,
) -> None:
    """An unknown alias raises RegistryError naming only the alias."""
    with pytest.raises(RegistryError) as excinfo:
        registry.get_engine("does-not-exist")

    assert "does-not-exist" in str(excinfo.value)


def test_describe_returns_alias_and_dialect_only(
    registry: ConnectionRegistry,
) -> None:
    """describe() exposes safe metadata without a connection string."""
    metadata = registry.describe("main")

    assert metadata == {"alias": "main", "dialect": "sqlite"}


def test_list_metadata_covers_every_alias(
    registry: ConnectionRegistry,
) -> None:
    """list_metadata() returns one entry per registered alias."""
    metadata = registry.list_metadata()

    aliases = {entry["alias"] for entry in metadata}
    assert aliases == {"main", "reporting"}
    assert all("url" not in entry for entry in metadata)


def test_dispose_clears_all_engines(
    registry: ConnectionRegistry,
) -> None:
    """dispose() empties the registry."""
    registry.dispose()

    assert registry.aliases() == []


def test_remove_unknown_alias_raises_registry_error(
    registry: ConnectionRegistry,
) -> None:
    """remove() on an unregistered alias raises RegistryError."""
    with pytest.raises(RegistryError):
        registry.remove("does-not-exist")


def test_sqlglot_dialect_maps_from_engine(
    registry: ConnectionRegistry,
) -> None:
    """A sqlite engine resolves to the sqlglot 'sqlite' dialect."""
    assert registry.sqlglot_dialect("main") == "sqlite"


def test_sqlglot_dialect_honors_entry_override(tmp_path: Path) -> None:
    """An explicit dialect in the config wins over the engine mapping."""
    path = _write_registry(
        tmp_path,
        """
        [databases.main]
        url = "sqlite://"
        dialect = "postgres"
        """,
    )
    config = AppConfig(config_file=path)
    registry = ConnectionRegistry.from_config(config)

    assert registry.sqlglot_dialect("main") == "postgres"


def test_sqlglot_dialect_unknown_alias_raises_registry_error(
    registry: ConnectionRegistry,
) -> None:
    """An unknown alias raises RegistryError, like get_engine."""
    with pytest.raises(RegistryError):
        registry.sqlglot_dialect("does-not-exist")


def _excluding_registry(tmp_path: Path) -> ConnectionRegistry:
    path = _write_registry(
        tmp_path,
        """
        [databases.main]
        url = "sqlite://"
        exclude_tables = ["Secrets", "billing.invoices"]
        """,
    )
    config = AppConfig(config_file=path)
    return ConnectionRegistry.from_config(config)


def test_is_excluded_bare_name_matches_any_schema(tmp_path: Path) -> None:
    """A bare denylist name excludes that table in every schema."""
    registry = _excluding_registry(tmp_path)

    assert registry.is_excluded("main", "secrets") is True
    assert registry.is_excluded("main", "secrets", schema="public") is True


def test_is_excluded_is_case_insensitive(tmp_path: Path) -> None:
    """Denylist matching ignores case."""
    registry = _excluding_registry(tmp_path)

    assert registry.is_excluded("main", "SECRETS") is True


def test_is_excluded_qualified_name_is_schema_specific(
    tmp_path: Path,
) -> None:
    """A schema-qualified denylist name only excludes that schema's table."""
    registry = _excluding_registry(tmp_path)

    assert registry.is_excluded("main", "invoices", schema="billing") is True
    assert registry.is_excluded("main", "invoices", schema="sales") is False
    assert registry.is_excluded("main", "invoices") is False


def test_is_excluded_false_without_denylist(
    registry: ConnectionRegistry,
) -> None:
    """A database with no denylist excludes nothing."""
    assert registry.is_excluded("main", "anything") is False


def test_credential_isolation_across_registry_surface(
    registry: ConnectionRegistry,
) -> None:
    """A configured password never appears in metadata or errors."""
    metadata_blob = repr(registry.list_metadata())
    describe_blob = repr(registry.describe("main"))

    assert "hunter2" not in metadata_blob
    assert "hunter2" not in describe_blob

    with pytest.raises(RegistryError) as excinfo:
        registry.get_engine("unknown-alias")
    assert "hunter2" not in str(excinfo.value)


def test_credential_isolation_on_connection_failure(
    tmp_path: Path,
) -> None:
    """A bad connection string never leaks its password in the error."""
    path = _write_registry(
        tmp_path,
        """
        [databases.broken]
        url = "postgresql+psycopg://user:hunter2@nonexistent-host/db"
        """,
    )
    config = AppConfig(config_file=path)

    with pytest.raises(RegistryError) as excinfo:
        ConnectionRegistry.from_config(config)

    message = str(excinfo.value)
    assert "hunter2" not in message
    assert "broken" in message
