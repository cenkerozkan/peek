"""Tests for ``peek db add`` command."""

from pathlib import Path

import pytest
from click.testing import CliRunner

from peek.cli import main as cli


def _run_add(
    tmp_path: Path,
    inputs: str,
    monkeypatch: pytest.MonkeyPatch,
) -> str:
    """Run ``peek db add`` with simulated interactive input.

    Returns the stderr output.
    """
    (tmp_path / ".peek").mkdir()
    (tmp_path / ".peek" / "databases.toml").write_text("[databases]\n")
    monkeypatch.chdir(tmp_path)

    runner = CliRunner()
    result = runner.invoke(cli, ["db", "add"], input=inputs)
    assert result.exit_code == 0, result.stderr
    return result.stderr


def test_add_with_valid_sqlite(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Adding a valid sqlite database persists the alias and URL."""
    stderr = _run_add(
        tmp_path,
        "mydb\n"
        "sqlite://\n"
        "\n"
        "\n",
        monkeypatch,
    )

    toml = tmp_path / ".peek" / "databases.toml"
    content = toml.read_text()
    assert "mydb" in content
    assert "sqlite://" in content
    assert "mydb" in stderr


def test_add_fails_on_bad_url(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A connection that cannot be established is rejected."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".peek").mkdir()
    (tmp_path / ".peek" / "databases.toml").write_text("[databases]\n")

    runner = CliRunner()
    result = runner.invoke(
        cli, ["db", "add"],
        input="baddb\npostgresql://bad:bad@localhost:1/nope\n\n\n",
    )

    assert result.exit_code == 1
    assert "Could not connect to database" in result.stderr

    toml = tmp_path / ".peek" / "databases.toml"
    content = toml.read_text()
    assert "baddb" not in content


def test_add_appends_to_existing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Running add twice produces two entries in the TOML."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".peek").mkdir()
    (tmp_path / ".peek" / "databases.toml").write_text("[databases]\n")

    runner = CliRunner()

    runner.invoke(
        cli, ["db", "add"],
        input="first\nsqlite://\n\n\n",
    )
    result = runner.invoke(
        cli, ["db", "add"],
        input="second\nsqlite://\n\n\n",
    )

    assert result.exit_code == 0, result.stderr

    toml = tmp_path / ".peek" / "databases.toml"
    content = toml.read_text()
    assert "first" in content
    assert "second" in content


def test_add_dialect_and_excludes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Non-empty dialect and exclude tables appear in the TOML."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".peek").mkdir()
    (tmp_path / ".peek" / "databases.toml").write_text("[databases]\n")

    runner = CliRunner()
    result = runner.invoke(
        cli, ["db", "add"],
        input="mydb\nsqlite://\npostgres\nsecret_tbl,audit_log\n",
    )

    assert result.exit_code == 0, result.stderr

    toml = tmp_path / ".peek" / "databases.toml"
    content = toml.read_text()
    assert "mydb" in content
    assert "postgres" in content
    assert "secret_tbl" in content
    assert "audit_log" in content


def test_add_output_goes_to_stderr(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """All output goes to stderr; stdout is clean."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".peek").mkdir()
    (tmp_path / ".peek" / "databases.toml").write_text("[databases]\n")

    runner = CliRunner()
    result = runner.invoke(
        cli, ["db", "add"],
        input="mydb\nsqlite://\n\n\n",
    )

    assert result.exit_code == 0
    assert result.stdout == ""
    assert "mydb" in result.stderr


def test_add_hides_connection_url_in_error_message(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Error message names only the alias, never the URL."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".peek").mkdir()
    (tmp_path / ".peek" / "databases.toml").write_text("[databases]\n")

    runner = CliRunner()
    result = runner.invoke(
        cli, ["db", "add"],
        input="mydb\npostgresql://admin:p@ssw0rd@host/db\n\n\n",
    )

    assert result.exit_code == 1

    # The error line should name only the alias
    for line in result.stderr.splitlines():
        if "Could not connect to database" in line:
            assert "mydb" in line
            assert "postgresql" not in line
            assert "p@ssw0rd" not in line
            assert "admin" not in line
            assert "host" not in line
            break
    else:
        pytest.fail("Could not connect to database error not found in stderr")
