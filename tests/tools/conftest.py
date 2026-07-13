"""Shared fixtures for the MCP tool-layer tests.

Builds a real ``AppContext`` over a temporary SQLite database and wraps it in
a stub context, so the module-level tools can be called directly -- exercising
the tool contract and error shaping without a running server or async client.
"""

from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import cast

import pytest
from fastmcp import Context
from sqlalchemy import create_engine, text

from peek.config import AppConfig
from peek.services.connection_registry import ConnectionRegistry
from peek.services.schema_service import SchemaService
from peek.services.sql_service import SqlService
from peek.tools.context import APP_CONTEXT_KEY, AppContext


@dataclass(frozen=True)
class ToolEnv:
    """A configured tool environment for a single test."""

    ctx: Context
    url: str


def _make_database(tmp_path: Path) -> str:
    db_path = tmp_path / "app.db"
    url = f"sqlite:///{db_path}"
    engine = create_engine(url)
    with engine.begin() as connection:
        connection.execute(
            text(
                "CREATE TABLE users ("
                "id INTEGER PRIMARY KEY, name TEXT NOT NULL)"
            )
        )
        connection.execute(
            text("CREATE TABLE secrets (id INTEGER, token TEXT)")
        )
        connection.execute(
            text("CREATE VIEW active_users AS SELECT id, name FROM users")
        )
        for index in range(3):
            connection.execute(
                text("INSERT INTO users (id, name) VALUES (:id, :name)"),
                {"id": index, "name": f"user{index}"},
            )
    engine.dispose()
    return url


def _stub_ctx(app: AppContext) -> Context:
    stub = SimpleNamespace(lifespan_context={APP_CONTEXT_KEY: app})
    return cast(Context, stub)


def make_env(tmp_path: Path, exclude: str = "") -> ToolEnv:
    """Build a ``ToolEnv`` over a SQLite database aliased ``main``."""
    url = _make_database(tmp_path)
    config_path = tmp_path / "databases.toml"
    body = f'[databases.main]\nurl = "{url}"\n'
    if exclude:
        body += f"exclude_tables = [{exclude}]\n"
    config_path.write_text(body)
    registry = ConnectionRegistry.from_config(
        AppConfig(config_file=config_path)
    )
    app = AppContext(
        registry=registry,
        schema_service=SchemaService(registry),
        sql_service=SqlService(registry, max_rows=1000),
    )
    return ToolEnv(ctx=_stub_ctx(app), url=url)


@pytest.fixture
def env(tmp_path: Path) -> ToolEnv:
    return make_env(tmp_path)


@pytest.fixture
def denied_env(tmp_path: Path) -> ToolEnv:
    return make_env(tmp_path, exclude='"secrets"')
