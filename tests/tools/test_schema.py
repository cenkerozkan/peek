"""Tests for the ``list_tables`` and ``get_schema`` tools."""

import pytest
from fastmcp.exceptions import ToolError

from peek.tools.schema import get_schema, list_tables
from tests.tools.conftest import ToolEnv


def test_list_tables_names_tables_and_views(env: ToolEnv) -> None:
    result = list_tables("main", env.ctx)
    names = {info.name for info in result.tables}
    assert {"users", "secrets", "active_users"} <= names
    assert result.hidden_count == 0


def test_list_tables_hides_denylisted_table(denied_env: ToolEnv) -> None:
    result = list_tables("main", denied_env.ctx)
    names = {info.name for info in result.tables}
    assert "secrets" not in names
    assert result.hidden_count == 1


def test_list_tables_unknown_alias_raises_tool_error(env: ToolEnv) -> None:
    with pytest.raises(ToolError) as caught:
        list_tables("nope", env.ctx)
    assert "nope" in str(caught.value)


def test_get_schema_returns_columns_and_primary_key(env: ToolEnv) -> None:
    result = get_schema("main", env.ctx, tables=["users"])
    (users,) = result.tables
    assert [column.name for column in users.columns] == ["id", "name"]
    assert users.primary_key == ["id"]


def test_get_schema_rejects_denylisted_table(denied_env: ToolEnv) -> None:
    with pytest.raises(ToolError):
        get_schema("main", denied_env.ctx, tables=["secrets"])


def test_get_schema_unknown_alias_raises_tool_error(env: ToolEnv) -> None:
    with pytest.raises(ToolError):
        get_schema("nope", env.ctx)
