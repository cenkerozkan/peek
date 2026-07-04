"""Tests for :class:`peek.config.AppConfig`."""

from pathlib import Path

import pytest

from src.peek.config import AppConfig


def test_default_resolved_config_file_ends_with_databases_toml() -> None:
    """With no override, the default lives in the platform config dir."""
    config = AppConfig()

    assert config.resolved_config_file().name == "databases.toml"


def test_explicit_config_file_is_honored(tmp_path: Path) -> None:
    """An explicit config_file takes priority over the default."""
    explicit = tmp_path / "custom.toml"
    config = AppConfig(config_file=explicit)

    assert config.resolved_config_file() == explicit


def test_env_var_overrides_max_rows(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """PEEK_MAX_ROWS overrides the default max_rows."""
    monkeypatch.setenv("PEEK_MAX_ROWS", "42")

    config = AppConfig()

    assert config.max_rows == 42
