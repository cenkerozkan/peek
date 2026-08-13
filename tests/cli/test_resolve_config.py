"""Tests for ``resolve_config_path`` in ``peek.config``."""

from pathlib import Path

import pytest

from peek.config import resolve_config_path


def test_local_peek_dir(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """.peek/databases.toml exists in cwd — returns local path."""
    local_dir = tmp_path / ".peek"
    local_dir.mkdir()
    (local_dir / "databases.toml").write_text("")

    monkeypatch.chdir(tmp_path)

    result = resolve_config_path()

    assert result == local_dir / "databases.toml"


def test_nothing_exists_returns_local(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Nothing exists anywhere.

    Returns cwd-local default so user sees peek init.
    """
    monkeypatch.chdir(tmp_path)

    result = resolve_config_path()

    assert result == tmp_path / ".peek" / "databases.toml"
