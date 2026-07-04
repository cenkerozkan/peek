"""Tests for the read-only SQL safety guard.

These tests are the contract for the safety chokepoint: any statement that
could mutate data or schema, run multiple statements, or evade parsing must be
rejected, and legitimate read-only queries must be accepted.
"""

from typing import Optional

import pytest
from sqlglot import exp

from src.peek.safety.guard import UnsafeSQLError, ensure_read_only

READ_ONLY_QUERIES = [
    "SELECT 1",
    "SELECT 1;",
    "select id, name from users where active = true",
    "SELECT * FROM t ORDER BY id LIMIT 10",
    "SELECT a FROM t1 UNION SELECT a FROM t2",
    "SELECT a FROM t1 INTERSECT SELECT a FROM t2",
    "WITH c AS (SELECT 1 AS n) SELECT n FROM c",
    "SELECT u.id, o.total FROM users u JOIN orders o ON o.user_id = u.id",
    "SELECT (SELECT count(*) FROM orders) AS n",
    "(SELECT 1)",
    "-- a leading comment\nSELECT 1",
]

MUTATING_STATEMENTS = [
    "INSERT INTO t VALUES (1)",
    "UPDATE t SET x = 1",
    "DELETE FROM t",
    "DROP TABLE t",
    "CREATE TABLE t (id int)",
    "ALTER TABLE t ADD COLUMN c int",
    "TRUNCATE TABLE t",
    "MERGE INTO t USING s ON t.id = s.id "
    "WHEN MATCHED THEN UPDATE SET t.x = s.x",
    "GRANT SELECT ON t TO bob",
]


@pytest.mark.parametrize("sql", READ_ONLY_QUERIES)
def test_accepts_read_only_queries(sql: str) -> None:
    """Legitimate read-only queries are accepted and parsed."""
    result = ensure_read_only(sql)
    assert isinstance(result, exp.Expression)


@pytest.mark.parametrize("sql", MUTATING_STATEMENTS)
def test_rejects_mutating_statements(sql: str) -> None:
    """Every data- or schema-modifying statement is rejected."""
    with pytest.raises(UnsafeSQLError):
        ensure_read_only(sql)


def test_rejects_stacked_statements() -> None:
    """A trailing statement cannot ride along after a SELECT."""
    with pytest.raises(UnsafeSQLError):
        ensure_read_only("SELECT * FROM t; DROP TABLE t")


def test_rejects_stacked_selects() -> None:
    """Even two SELECTs are rejected: exactly one statement is allowed."""
    with pytest.raises(UnsafeSQLError):
        ensure_read_only("SELECT 1; SELECT 2")


def test_rejects_data_modifying_cte() -> None:
    """A write hidden inside a CTE is caught by the full-tree scan."""
    sql = "WITH x AS (INSERT INTO t VALUES (1) RETURNING id) SELECT * FROM x"
    with pytest.raises(UnsafeSQLError):
        ensure_read_only(sql, dialect="postgres")


def test_rejects_write_in_subquery() -> None:
    """A write nested in a subquery is caught even under a SELECT root."""
    sql = "SELECT * FROM (DELETE FROM t RETURNING *) AS d"
    with pytest.raises(UnsafeSQLError):
        ensure_read_only(sql, dialect="postgres")


def test_rejects_unparsed_command() -> None:
    """Statements sqlglot cannot model (for example VACUUM) are rejected."""
    with pytest.raises(UnsafeSQLError):
        ensure_read_only("VACUUM")


@pytest.mark.parametrize("sql", ["", "   ", "\n\t", ";"])
def test_rejects_empty_input(sql: str) -> None:
    """Empty or whitespace-only input is rejected."""
    with pytest.raises(UnsafeSQLError):
        ensure_read_only(sql)


def test_rejects_unparseable_sql() -> None:
    """Syntactic garbage is rejected rather than passed through."""
    with pytest.raises(UnsafeSQLError):
        ensure_read_only("SELECT FROM WHERE )(")


def test_error_message_has_no_raw_sql_or_url() -> None:
    """Guard messages describe the violation without echoing the input."""
    secret = "postgresql://user:hunter2@host/db"
    try:
        ensure_read_only(f"DELETE FROM t WHERE note = '{secret}'")
    except UnsafeSQLError as error:
        message = str(error)
        assert secret not in message
        assert "hunter2" not in message
    else:
        pytest.fail("expected UnsafeSQLError")


def test_returns_reusable_expression() -> None:
    """The returned root can be reused without re-parsing."""
    dialect: Optional[str] = None
    root = ensure_read_only("SELECT 1 AS n", dialect=dialect)
    assert root.sql().lower().startswith("select")
