"""Tests for the ``validate_sql`` and ``run_sql`` tools."""

import pytest
from fastmcp.exceptions import ToolError

from peek.models.query import QueryResult, ValidationResult
from peek.tools.sql import run_sql, validate_sql
from tests.tools.conftest import ToolEnv


def test_validate_accepts_read_only_select(env: ToolEnv) -> None:
    result = validate_sql("main", env.ctx, "SELECT id FROM users")
    assert result == ValidationResult(alias="main", valid=True, message=None)


def test_validate_refuses_mutation_as_verdict(env: ToolEnv) -> None:
    result = validate_sql("main", env.ctx, "DELETE FROM users")
    assert isinstance(result, ValidationResult)
    assert result.valid is False
    assert result.message


def test_validate_refuses_denylisted_table_as_verdict(
    denied_env: ToolEnv,
) -> None:
    result = validate_sql("main", denied_env.ctx, "SELECT * FROM secrets")
    assert result.valid is False


def test_validate_unknown_alias_raises_tool_error(env: ToolEnv) -> None:
    with pytest.raises(ToolError):
        validate_sql("nope", env.ctx, "SELECT 1")


def test_run_returns_rows_for_select(env: ToolEnv) -> None:
    result = run_sql("main", env.ctx, "SELECT id, name FROM users ORDER BY id")
    assert isinstance(result, QueryResult)
    assert result.columns == ["id", "name"]
    assert result.row_count == 3
    assert result.rows[0] == [0, "user0"]


def test_run_refuses_mutation(env: ToolEnv) -> None:
    with pytest.raises(ToolError):
        run_sql("main", env.ctx, "DELETE FROM users")


def test_run_refuses_denylisted_table(denied_env: ToolEnv) -> None:
    with pytest.raises(ToolError):
        run_sql("main", denied_env.ctx, "SELECT * FROM secrets")


def test_run_unknown_alias_raises_tool_error(env: ToolEnv) -> None:
    with pytest.raises(ToolError) as caught:
        run_sql("nope", env.ctx, "SELECT 1")
    assert "nope" in str(caught.value)


def test_run_database_error_stays_credential_safe(env: ToolEnv) -> None:
    with pytest.raises(ToolError) as caught:
        run_sql("main", env.ctx, "SELECT missing FROM users")
    message = str(caught.value)
    assert env.url not in message
    assert "sqlite" not in message.lower()
