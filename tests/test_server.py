"""Tests for the FastMCP entry point and its lifespan.

Drives the real lifespan over a temporary SQLite database -- pointed at via
``PEEK_CONFIG_FILE``, the same env var a deployed server reads -- so the wiring
is exercised end to end: the services are built once, published under
``APP_CONTEXT_KEY`` for the tool layer, and every engine is disposed on
shutdown.
"""

import asyncio
from pathlib import Path
from typing import Any, Callable, List

import pytest
from fastmcp import FastMCP
from sqlalchemy import create_engine, text

from peek.errors import ConfigError
from peek.server import build_server, lifespan, main
from peek.services.connection_registry import ConnectionRegistry
from peek.services.schema_service import SchemaService
from peek.services.sql_service import SqlService
from peek.tools.context import APP_CONTEXT_KEY, AppContext

EXPECTED_TOOLS = {
    "list_databases",
    "list_tables",
    "get_schema",
    "validate_sql",
    "run_sql",
}


def _write_registry(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Create a SQLite database and point ``PEEK_CONFIG_FILE`` at its alias."""
    db_path = tmp_path / "app.db"
    # as_posix(): a Windows path's backslashes would be read as escape
    # sequences inside the TOML basic string below.
    url = f"sqlite:///{db_path.as_posix()}"
    engine = create_engine(url)
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE users (id INTEGER PRIMARY KEY)"))
    engine.dispose()

    config_path = tmp_path / "databases.toml"
    config_path.write_text(f'[databases.main]\nurl = "{url}"\n')
    monkeypatch.setenv("PEEK_CONFIG_FILE", str(config_path))
    return config_path


def _in_lifespan(server: FastMCP, inspect: Callable[[AppContext], Any]) -> Any:
    """Run ``inspect`` against the live ``AppContext``, inside the lifespan.

    The inspection has to happen before the lifespan exits: shutdown disposes
    the engines and empties the registry, so a context captured on the way out
    no longer reflects a running server.
    """

    async def drive() -> Any:
        async with lifespan(server) as context:
            return inspect(context[APP_CONTEXT_KEY])

    return asyncio.run(drive())


def test_build_server_masks_error_details() -> None:
    """Unexpected exceptions must never reach the client (credential safety).

    FastMCP exposes the flag only privately, so this asserts on the private
    attribute rather than leaving the guarantee untested.
    """
    assert build_server()._mask_error_details is True


def test_build_server_registers_every_tool() -> None:
    server = build_server()

    tools = asyncio.run(server.list_tools())

    assert {tool.name for tool in tools} == EXPECTED_TOOLS


def test_lifespan_publishes_app_context(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The tool layer's seam is populated with the built services."""
    _write_registry(tmp_path, monkeypatch)

    types = _in_lifespan(
        build_server(),
        lambda app: (
            isinstance(app, AppContext),
            isinstance(app.registry, ConnectionRegistry),
            isinstance(app.schema_service, SchemaService),
            isinstance(app.sql_service, SqlService),
        ),
    )

    assert types == (True, True, True, True)


def test_lifespan_registers_configured_aliases(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_registry(tmp_path, monkeypatch)

    aliases = _in_lifespan(build_server(), lambda app: app.registry.aliases())

    assert aliases == ["main"]


def test_lifespan_shares_one_registry_across_services(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Services are built once over the same registry, not per request."""
    _write_registry(tmp_path, monkeypatch)

    shared = _in_lifespan(
        build_server(),
        lambda app: (
            app.schema_service._registry is app.registry,
            app.sql_service._registry is app.registry,
        ),
    )

    assert shared == (True, True)


def test_lifespan_disposes_engines_on_shutdown(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Shutdown must return every pooled connection, even on a clean exit."""
    _write_registry(tmp_path, monkeypatch)
    server = build_server()
    captured: List[Any] = []

    async def drive() -> None:
        async with lifespan(server) as context:
            registry = context[APP_CONTEXT_KEY].registry
            engine = registry.get_engine("main")
            captured.append((registry, engine, engine.pool))

    asyncio.run(drive())

    registry, engine, pool_before = captured[0]
    assert registry.aliases() == []
    # Engine.dispose() swaps in a fresh pool, so a new pool proves it ran.
    assert engine.pool is not pool_before


def test_lifespan_disposes_engines_when_the_body_raises(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A crash mid-session must not leak the connection pool."""
    _write_registry(tmp_path, monkeypatch)
    server = build_server()
    captured: List[Any] = []

    async def drive() -> None:
        async with lifespan(server) as context:
            captured.append(context[APP_CONTEXT_KEY].registry)
            raise RuntimeError("boom")

    with pytest.raises(RuntimeError):
        asyncio.run(drive())

    assert captured[0].aliases() == []


def test_lifespan_fails_when_the_config_file_is_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("PEEK_CONFIG_FILE", str(tmp_path / "absent.toml"))

    with pytest.raises(ConfigError):
        _in_lifespan(build_server(), lambda app: None)


def test_main_runs_the_server_over_stdio(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The MCP channel is stdout, so the banner must never land there."""
    served: List[Any] = []
    monkeypatch.setattr(
        FastMCP,
        "run",
        lambda self, **kwargs: served.append((self, kwargs)),
    )

    main()

    assert len(served) == 1
    server, kwargs = served[0]
    assert server.name == "peek"
    assert kwargs["transport"] == "stdio"
    assert kwargs["show_banner"] is False
