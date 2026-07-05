"""MCP tool for discovering the databases the server can reach.

Thin wrapper over :class:`~src.peek.services.connection_registry`. Exposes only
``list_databases`` -- registering or removing a database is a startup/admin
concern, never a model-facing tool.
"""

from typing import List

from fastmcp import Context, FastMCP
from fastmcp.exceptions import ToolError

from src.peek.errors import PeekError
from src.peek.models.database import DatabaseInfo
from src.peek.tools.context import app_context


def list_databases(ctx: Context) -> List[DatabaseInfo]:
    """List every database this server can query, by alias.

    Call this first to learn which aliases exist; every other tool takes one
    of these aliases as its ``db`` argument. Returns aliases and safe metadata
    only -- never a connection string or credential.

    Args:
        ctx: The FastMCP request context (injected).

    Returns:
        One ``DatabaseInfo`` (alias and dialect) per registered database.
    """
    try:
        metadata = app_context(ctx).registry.list_metadata()
    except PeekError as error:
        raise ToolError(str(error)) from error
    return [DatabaseInfo(**entry) for entry in metadata]


def register(mcp: FastMCP) -> None:
    """Attach this module's tools to ``mcp``."""
    mcp.tool(list_databases)
