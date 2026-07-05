"""Tests for the read-only SQL execution chokepoint."""

from pathlib import Path

import pytest
from sqlalchemy import create_engine, text
from sqlglot import exp

from src.peek.config import AppConfig
from src.peek.errors import QueryError
from src.peek.safety.guard import UnsafeSQLError
from src.peek.services.connection_registry import ConnectionRegistry
from src.peek.services.sql_service import ExcludedTableError, SqlService


def _make_database(tmp_path: Path, rows: int = 3) -> str:
    db_path = tmp_path / "app.db"
    url = f"sqlite:///{db_path}"
    engine = create_engine(url)
    with engine.begin() as connection:
        connection.execute(
            text(
                "CREATE TABLE users ("
                "id INTEGER PRIMARY KEY, name TEXT NOT NULL, "
                "balance NUMERIC, joined DATE)"
            )
        )
        connection.execute(
            text("CREATE TABLE secrets (id INTEGER, token TEXT)")
        )
        for index in range(rows):
            connection.execute(
                text(
                    "INSERT INTO users (id, name, balance, joined) "
                    "VALUES (:id, :name, :balance, :joined)"
                ),
                {
                    "id": index,
                    "name": f"user{index}",
                    "balance": 10.5,
                    "joined": "2026-07-05",
                },
            )
    engine.dispose()
    return url


def _service(
    tmp_path: Path,
    url: str,
    max_rows: int = 1000,
    exclude: str = "",
) -> SqlService:
    config_path = tmp_path / "databases.toml"
    body = f'[databases.main]\nurl = "{url}"\n'
    if exclude:
        body += f"exclude_tables = [{exclude}]\n"
    config_path.write_text(body)
    config = AppConfig(config_file=config_path)
    registry = ConnectionRegistry.from_config(config)
    return SqlService(registry, max_rows=max_rows)


@pytest.fixture
def service(tmp_path: Path) -> SqlService:
    return _service(tmp_path, _make_database(tmp_path))


def test_execute_returns_columns_and_list_of_lists(
    service: SqlService,
) -> None:
    """A SELECT returns column names and positional rows."""
    result = service.execute("main", "SELECT id, name FROM users ORDER BY id")

    assert result.columns == ["id", "name"]
    assert result.rows == [[0, "user0"], [1, "user1"], [2, "user2"]]
    assert result.row_count == 3
    assert result.truncated is False


@pytest.mark.parametrize(
    "sql",
    [
        "INSERT INTO users (id, name) VALUES (99, 'x')",
        "UPDATE users SET name = 'x'",
        "DELETE FROM users",
        "DROP TABLE users",
        "SELECT 1; SELECT 2",
    ],
)
def test_mutating_or_stacked_sql_is_rejected_and_runs_nothing(
    tmp_path: Path, sql: str
) -> None:
    """Non-SELECT and stacked statements raise and never touch the database."""
    url = _make_database(tmp_path)
    service = _service(tmp_path, url)

    with pytest.raises(UnsafeSQLError):
        service.execute("main", sql)

    remaining = service.execute("main", "SELECT COUNT(*) FROM users")
    assert remaining.rows == [[3]]


def test_excluded_table_query_is_rejected(tmp_path: Path) -> None:
    """A query naming a denylisted table raises without leaking details."""
    url = _make_database(tmp_path)
    service = _service(tmp_path, url, exclude='"secrets"')

    with pytest.raises(ExcludedTableError) as excinfo:
        service.execute("main", "SELECT token FROM secrets")

    message = str(excinfo.value)
    assert "not permitted" in message
    assert "secrets" not in message
    assert url not in message


def test_excluded_table_in_subquery_is_rejected(tmp_path: Path) -> None:
    """Exclusion is enforced inside subqueries and CTEs, not just top level."""
    url = _make_database(tmp_path)
    service = _service(tmp_path, url, exclude='"secrets"')

    with pytest.raises(ExcludedTableError):
        service.execute(
            "main",
            "SELECT id FROM users WHERE id IN (SELECT id FROM secrets)",
        )
    with pytest.raises(ExcludedTableError):
        service.execute(
            "main",
            "WITH s AS (SELECT id FROM secrets) SELECT * FROM s",
        )


def test_row_cap_truncates_and_flags(tmp_path: Path) -> None:
    """The row cap limits returned rows and sets the truncated flag."""
    url = _make_database(tmp_path, rows=5)
    service = _service(tmp_path, url, max_rows=2)

    result = service.execute("main", "SELECT id FROM users ORDER BY id")
    assert result.row_count == 2
    assert result.rows == [[0], [1]]
    assert result.truncated is True


def test_row_cap_not_flagged_when_under_limit(tmp_path: Path) -> None:
    """Truncated is False when the full result fits under the cap."""
    url = _make_database(tmp_path, rows=2)
    service = _service(tmp_path, url, max_rows=10)

    result = service.execute("main", "SELECT id FROM users")
    assert result.row_count == 2
    assert result.truncated is False


def test_values_are_coerced_json_safe(service: SqlService) -> None:
    """Numeric and date columns serialize to JSON-safe primitives."""
    result = service.execute(
        "main", "SELECT balance, joined FROM users LIMIT 1"
    )

    balance, joined = result.rows[0]
    assert isinstance(balance, float)
    assert isinstance(joined, str)


def test_validate_returns_parsed_root_for_valid_query(
    service: SqlService,
) -> None:
    """Validate returns the parsed expression without executing anything."""
    root = service.validate("main", "SELECT id FROM users")
    assert isinstance(root, exp.Expression)


def test_output_and_errors_carry_no_connection_string(
    tmp_path: Path,
) -> None:
    """No result or error ever echoes the connection string."""
    url = _make_database(tmp_path)
    service = _service(tmp_path, url)

    result = service.execute("main", "SELECT id FROM users")
    assert url not in repr(result)

    with pytest.raises(QueryError) as excinfo:
        service.execute("main", "SELECT nope FROM users")
    assert url not in str(excinfo.value)
