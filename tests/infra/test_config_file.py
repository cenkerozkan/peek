"""Tests for :mod:`peek.infra.config_file`."""

from pathlib import Path

import pytest

from peek.errors import ConfigError
from peek.infra.config_file import load_registry, remove_entry, save_entry
from peek.models.config import DatabaseEntry

VALID_TOML = """
[databases.psql]
url = "postgresql+psycopg://user:hunter2@host:5432/db"
dialect = "postgres"

[databases.warehouse]
url = "sqlite:///warehouse.db"
"""


def _write(tmp_path: Path, content: str) -> Path:
    path = tmp_path / "databases.toml"
    path.write_text(content)
    return path


def test_valid_file_yields_aliases_and_dialect(tmp_path: Path) -> None:
    """A well-formed file resolves to the expected aliases and dialect."""
    path = _write(tmp_path, VALID_TOML)

    registry = load_registry(path)

    assert set(registry) == {"psql", "warehouse"}
    assert registry["psql"].dialect == "postgres"
    assert registry["warehouse"].dialect is None


def test_missing_file_raises_config_error(tmp_path: Path) -> None:
    """A nonexistent path raises ConfigError."""
    path = tmp_path / "does-not-exist.toml"

    with pytest.raises(ConfigError):
        load_registry(path)


def test_malformed_toml_raises_config_error(tmp_path: Path) -> None:
    """Syntactically invalid TOML raises ConfigError."""
    path = _write(tmp_path, "this is not [ valid toml")

    with pytest.raises(ConfigError):
        load_registry(path)


def test_empty_registry_raises_config_error(tmp_path: Path) -> None:
    """A file declaring zero databases is rejected."""
    path = _write(tmp_path, "")

    with pytest.raises(ConfigError):
        load_registry(path)


def test_config_error_message_has_no_secret(tmp_path: Path) -> None:
    """The raised message references only the path, never the URL."""
    path = _write(tmp_path, "this is not [ valid toml")

    with pytest.raises(ConfigError) as excinfo:
        load_registry(path)

    message = str(excinfo.value)
    assert "hunter2" not in message
    assert "postgresql" not in message
    assert str(path) in message


def test_save_entry_creates_new_file(tmp_path: Path) -> None:
    """A missing path is created with the new entry and round-trips."""
    path = tmp_path / "databases.toml"
    entry = DatabaseEntry(url="postgresql+psycopg://u:p@h:5432/db")

    save_entry(path, "newdb", entry)

    assert path.is_file()
    registry = load_registry(path)
    assert "newdb" in registry
    assert (
        registry["newdb"].url.get_secret_value()
        == "postgresql+psycopg://u:p@h:5432/db"
    )


def test_save_entry_appends_to_existing(tmp_path: Path) -> None:
    """Saving a second alias keeps the first entry intact."""
    path = _write(tmp_path, VALID_TOML)
    entry = DatabaseEntry(url="sqlite:///extra.db")

    save_entry(path, "extra", entry)

    registry = load_registry(path)
    assert set(registry) == {"psql", "warehouse", "extra"}
    assert registry["extra"].url.get_secret_value() == "sqlite:///extra.db"


def test_save_entry_overwrites_existing_alias(tmp_path: Path) -> None:
    """Re-saving the same alias replaces the old URL."""
    path = _write(tmp_path, VALID_TOML)
    entry = DatabaseEntry(url="sqlite:///overwritten.db")

    save_entry(path, "psql", entry)

    registry = load_registry(path)
    assert (
        registry["psql"].url.get_secret_value() == "sqlite:///overwritten.db"
    )


def test_save_entry_omits_defaults(tmp_path: Path) -> None:
    """Entries with default dialect/exclude_tables omit those keys."""
    path = tmp_path / "databases.toml"
    entry = DatabaseEntry(url="sqlite:///minimal.db")

    save_entry(path, "minimal", entry)

    registry = load_registry(path)
    assert registry["minimal"].url.get_secret_value() == "sqlite:///minimal.db"
    assert registry["minimal"].dialect is None
    assert registry["minimal"].exclude_tables == []
    content = path.read_text()
    assert "dialect" not in content
    assert "exclude_tables" not in content


def test_remove_entry_removes_alias(tmp_path: Path) -> None:
    """Removing one alias leaves the other entries intact."""
    path = _write(tmp_path, VALID_TOML)

    remove_entry(path, "psql")

    registry = load_registry(path)
    assert set(registry) == {"warehouse"}


def test_remove_entry_unknown_alias(tmp_path: Path) -> None:
    """Removing a non-existent alias raises ConfigError."""
    path = _write(tmp_path, VALID_TOML)

    with pytest.raises(ConfigError):
        remove_entry(path, "nonexistent")


def test_remove_entry_missing_file(tmp_path: Path) -> None:
    """Removing from a non-existent file raises ConfigError."""
    path = tmp_path / "does-not-exist.toml"

    with pytest.raises(ConfigError):
        remove_entry(path, "any")
