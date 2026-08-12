"""Tests for ``peek init`` command."""

from pathlib import Path

import pytest
from click.testing import CliRunner

from peek.cli import main as cli


def test_init_creates_peek_dir(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Init creates .peek/ and databases.toml with commented example."""
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    result = runner.invoke(cli, ["init"])
    assert result.exit_code == 0, result.stderr

    peek_dir = Path(".peek")
    assert peek_dir.exists()
    toml = peek_dir / "databases.toml"
    assert toml.exists()
    content = toml.read_text()
    assert "[databases" in content


def test_init_creates_gitignore(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Init creates .gitignore when it does not exist."""
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    result = runner.invoke(cli, ["init"])
    assert result.exit_code == 0

    gitignore = Path(".gitignore")
    assert gitignore.exists()
    assert ".peek/" in gitignore.read_text()


def test_init_appends_to_existing_gitignore(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Init appends .peek/ without destroying existing .gitignore content."""
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    gitignore = Path(".gitignore")
    gitignore.write_text("__pycache__/\n*.pyc\n")

    result = runner.invoke(cli, ["init"])
    assert result.exit_code == 0

    content = gitignore.read_text()
    assert "__pycache__/" in content
    assert "*.pyc" in content
    assert ".peek/" in content


def test_init_skips_gitignore_if_already_listed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Init does not duplicate .peek/ in .gitignore."""
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    gitignore = Path(".gitignore")
    gitignore.write_text(".peek/\n")

    result = runner.invoke(cli, ["init"])
    assert result.exit_code == 0

    content = gitignore.read_text()
    assert content.count(".peek/") == 1


def test_init_refuses_if_already_initialized(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Init exits with code 1 when .peek/ already exists."""
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    Path(".peek").mkdir()

    result = runner.invoke(cli, ["init"])

    assert result.exit_code == 1
    assert "Already initialized" in result.stderr


def test_init_output_goes_to_stderr(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Init writes all output to stderr, not stdout."""
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    result = runner.invoke(cli, ["init"])

    assert result.stdout == ""
