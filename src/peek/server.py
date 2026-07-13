"""FastMCP entry point: builds the services once and serves the tools.

The lifespan constructs the :class:`ConnectionRegistry` and the schema and SQL
services a single time at startup, yields them as an :class:`AppContext` under
:data:`APP_CONTEXT_KEY` (the seam the thin tool layer reads through), and
disposes every engine on shutdown. The server is built with
``mask_error_details=True`` so any unexpected, non-``ToolError`` exception is
hidden from the client -- the second half of the credential-isolation
guarantee the tools rely on (see `docs/architecture.md` -> "Credential
isolation").
"""

from contextlib import asynccontextmanager
from typing import AsyncIterator, Dict

from fastmcp import FastMCP

from peek.config import AppConfig
from peek.services.connection_registry import ConnectionRegistry
from peek.services.schema_service import SchemaService
from peek.services.sql_service import SqlService
from peek.tools import register
from peek.tools.context import APP_CONTEXT_KEY, AppContext


@asynccontextmanager
async def lifespan(server: FastMCP) -> AsyncIterator[Dict[str, AppContext]]:
    """Build the services at startup and dispose their engines at shutdown.

    Args:
        server: The FastMCP server being started (unused; required by the
            lifespan protocol).

    Yields:
        A mapping under :data:`APP_CONTEXT_KEY` holding the long-lived
        services the tool layer resolves via ``app_context``.
    """
    config = AppConfig()
    registry = ConnectionRegistry.from_config(config)
    try:
        app = AppContext(
            registry=registry,
            schema_service=SchemaService(registry),
            sql_service=SqlService(registry, config.max_rows),
        )
        yield {APP_CONTEXT_KEY: app}
    finally:
        registry.dispose()


def build_server() -> FastMCP:
    """Construct the peek FastMCP server with its lifespan and tools.

    Returns:
        A configured ``FastMCP`` instance ready to ``run``. Built with
        ``mask_error_details=True`` so unexpected exceptions never leak a
        connection string to the client.
    """
    mcp: FastMCP = FastMCP(
        name="peek",
        instructions=(
            "Safe, read-only, multi-database SQL access. Call "
            "list_databases first to discover aliases, then use them as the "
            "db argument to the schema and query tools."
        ),
        lifespan=lifespan,
        mask_error_details=True,
    )
    register(mcp)
    return mcp


def main() -> None:
    """Run the peek server over stdio (console/``python -m`` entry point).

    stdout is the MCP channel: anything else written there corrupts the
    protocol, so the transport is pinned to stdio and the startup banner is
    suppressed rather than left to a framework default.
    """
    build_server().run(transport="stdio", show_banner=False)


if __name__ == "__main__":
    main()
