"""Tests for :mod:`peek.infra.config_file`."""

from pathlib import Path

import pytest

from src.peek.errors import ConfigError
from src.peek.infra.config_file import load_registry

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
