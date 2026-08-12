"""Tests for ``peek db remove`` command."""

from pathlib import Path

import pytest
from click.testing import CliRunner

from peek.cli import main as cli


def _make_toml(tmp_path: Path, entries: dict) -> Path:
    """Write a databases.toml file and return its path."""
    toml_lines = ["[databases]"]
    for alias, url in entries.items():
        toml_lines.append(f"[databases.{alias}]")
        toml_lines.append(f'url = "{url}"')
    toml_path = tmp_path / ".peek" / "databases.toml"
    toml_path.parent.mkdir(parents=True, exist_ok=True)
    toml_path.write_text("\n".join(toml_lines) + "\n")
    return toml_path


def test_remove_existing_alias(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Removing an existing alias removes it from the TOML."""
    _make_toml(
        tmp_path,
        {
            "first": "sqlite:///first.db",
            "second": "sqlite:///second.db",
        },
    )
    monkeypatch.chdir(tmp_path)

    runner = CliRunner()
    result = runner.invoke(cli, ["db", "remove"], input="first\n")

    assert result.exit_code == 0, result.stderr

    content = tmp_path / ".peek" / "databases.toml"
    content_text = content.read_text()
    assert "first" not in content_text
    assert "second" in content_text


def test_remove_unknown_alias(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Removing a non-existent alias exits with code 1."""
    _make_toml(
        tmp_path,
        {
            "first": "sqlite:///first.db",
        },
    )
    monkeypatch.chdir(tmp_path)

    runner = CliRunner()
    result = runner.invoke(cli, ["db", "remove"], input="ghost\n")

    assert result.exit_code == 1


def test_remove_no_config_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Removing when no config file exists shows an error."""
    monkeypatch.chdir(tmp_path)

    runner = CliRunner()
    result = runner.invoke(cli, ["db", "remove"], input="first\n")

    assert result.exit_code == 1
    assert "peek init" in result.stderr


def test_remove_shows_available_aliases(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The command lists available aliases before prompting."""
    _make_toml(
        tmp_path,
        {
            "alpha": "sqlite:///alpha.db",
            "beta": "sqlite:///beta.db",
        },
    )
    monkeypatch.chdir(tmp_path)

    runner = CliRunner()
    result = runner.invoke(cli, ["db", "remove"], input="alpha\n")

    assert "alpha" in result.stderr
    assert "beta" in result.stderr
    assert "Available database aliases" in result.stderr
