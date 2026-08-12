"""Tests for ``peek db list`` command."""

from pathlib import Path

import pytest
from click.testing import CliRunner

from peek.cli import main as cli


def _make_toml(tmp_path: Path, entries: dict) -> Path:
    """Write a databases.toml file and return its path."""
    toml_lines = ["[databases]"]
    for alias, data in entries.items():
        toml_lines.append(f"[databases.{alias}]")
        toml_lines.append(f'url = "{data["url"]}"')
        if "dialect" in data:
            toml_lines.append(f'dialect = "{data["dialect"]}"')
    toml_path = tmp_path / ".peek" / "databases.toml"
    toml_path.parent.mkdir(parents=True, exist_ok=True)
    toml_path.write_text("\n".join(toml_lines) + "\n")
    return toml_path


def test_list_shows_aliases(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Both aliases appear in stderr output."""
    _make_toml(
        tmp_path,
        {
            "psql": {"url": "postgresql+psycopg://u:p@host/db1"},
            "sqlite": {"url": "sqlite:///dev.db"},
        },
    )
    monkeypatch.chdir(tmp_path)

    runner = CliRunner()
    result = runner.invoke(cli, ["db", "list"])

    assert result.exit_code == 0, result.stderr
    assert "psql" in result.stderr
    assert "sqlite" in result.stderr


def test_list_shows_dialect(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An entry with dialect = postgres shows postgres."""
    _make_toml(
        tmp_path,
        {
            "pg": {
                "url": "postgresql+psycopg://u:p@host/db",
                "dialect": "postgres",
            },
        },
    )
    monkeypatch.chdir(tmp_path)

    runner = CliRunner()
    result = runner.invoke(cli, ["db", "list"])

    assert result.exit_code == 0, result.stderr
    assert "postgres" in result.stderr


def test_list_auto_dialect(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An entry without a dialect field shows auto."""
    _make_toml(
        tmp_path,
        {
            "sqlite": {"url": "sqlite:///dev.db"},
        },
    )
    monkeypatch.chdir(tmp_path)

    runner = CliRunner()
    result = runner.invoke(cli, ["db", "list"])

    assert result.exit_code == 0, result.stderr
    assert "auto" in result.stderr


def test_list_no_config_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Command exits with code 1 when no TOML file exists."""
    monkeypatch.chdir(tmp_path)

    runner = CliRunner()
    result = runner.invoke(cli, ["db", "list"])

    assert result.exit_code == 1
    assert "peek init" in result.stderr


def test_list_no_urls_in_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """No URL substring appears anywhere in stdout or stderr."""
    _make_toml(
        tmp_path,
        {
            "db_alpha": {
                "url": "postgresql+psycopg://admin:secret@db.example.com:5432/mydb",
            },
            "db_beta": {
                "url": "sqlite+aiosqlite:///path/to/secrets.db",
            },
        },
    )
    monkeypatch.chdir(tmp_path)

    runner = CliRunner()
    result = runner.invoke(cli, ["db", "list"])

    assert result.exit_code == 0, result.stderr
    combined = result.stdout + result.stderr
    assert "admin" not in combined
    assert "secret" not in combined
    assert "db.example.com" not in combined
    assert "mydb" not in combined
    assert "aiosqlite" not in combined
    assert "secrets.db" not in combined
