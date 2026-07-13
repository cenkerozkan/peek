"""Tests for the ``list_databases`` tool."""

from peek.models.database import DatabaseInfo
from peek.tools.databases import list_databases
from tests.tools.conftest import ToolEnv


def test_lists_registered_alias_and_dialect(env: ToolEnv) -> None:
    result = list_databases(env.ctx)
    assert result == [DatabaseInfo(alias="main", dialect="sqlite")]


def test_returns_typed_models(env: ToolEnv) -> None:
    result = list_databases(env.ctx)
    assert all(isinstance(info, DatabaseInfo) for info in result)


def test_never_reveals_the_connection_url(env: ToolEnv) -> None:
    result = list_databases(env.ctx)
    rendered = " ".join(info.model_dump_json() for info in result)
    assert env.url not in rendered
    assert "sqlite:///" not in rendered
