"""The dependency seam between the MCP tool layer and the services.

The FastMCP server's lifespan (Phase 7) builds the connection registry and the
services once and yields them in its lifespan context dict under
:data:`APP_CONTEXT_KEY`. Tools reach them only through :func:`app_context`, so
this is the single place the lifespan-context shape is known -- keeping tool
bodies thin and decoupled from server wiring.
"""

from dataclasses import dataclass

from fastmcp import Context

from src.peek.services.connection_registry import ConnectionRegistry
from src.peek.services.schema_service import SchemaService
from src.peek.services.sql_service import SqlService

APP_CONTEXT_KEY = "app"


@dataclass(frozen=True)
class AppContext:
    """The long-lived services a tool needs, built once at startup.

    Attributes:
        registry: Resolves aliases to validated engines and safe metadata.
        schema_service: Reads tables, views, and columns.
        sql_service: Validates and executes read-only queries.
    """

    registry: ConnectionRegistry
    schema_service: SchemaService
    sql_service: SqlService


def app_context(ctx: Context) -> AppContext:
    """Return the injected services for the current request.

    Args:
        ctx: The FastMCP context passed to the tool.

    Returns:
        The ``AppContext`` the server's lifespan placed in the context.
    """
    return ctx.lifespan_context[APP_CONTEXT_KEY]
