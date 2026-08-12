"""Tests for ``resolve_config_path`` in ``peek.cli``."""

from pathlib import Path
from unittest.mock import patch

import pytest

from peek.cli import resolve_config_path


def test_env_var_takes_priority(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """PEEK_CONFIG_FILE env var wins over a local .peek/databases.toml."""
    env_file = tmp_path / "env_config.toml"
    env_file.write_text("")

    local_dir = tmp_path / ".peek"
    local_dir.mkdir()
    (local_dir / "databases.toml").write_text("")

    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("PEEK_CONFIG_FILE", str(env_file))

    result = resolve_config_path()

    assert result == env_file


def test_local_peek_dir(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """No env var, .peek/databases.toml exists in cwd — returns local path."""
    local_dir = tmp_path / ".peek"
    local_dir.mkdir()
    (local_dir / "databases.toml").write_text("")

    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("PEEK_CONFIG_FILE", raising=False)

    result = resolve_config_path()

    assert result == local_dir / "databases.toml"


def test_platform_fallback(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """No env var, no local .peek/ — falls back to platform dir."""
    platform_dir = tmp_path / "platform"
    platform_dir.mkdir()
    (platform_dir / "databases.toml").write_text("")

    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("PEEK_CONFIG_FILE", raising=False)

    with patch("peek.cli.user_config_dir", return_value=str(platform_dir)):
        result = resolve_config_path()

    assert result == platform_dir / "databases.toml"


def test_nothing_exists_returns_local(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Nothing exists anywhere.

    Returns cwd-local default so user sees peek init.
    """
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("PEEK_CONFIG_FILE", raising=False)

    result = resolve_config_path()

    assert result == tmp_path / ".peek" / "databases.toml"
