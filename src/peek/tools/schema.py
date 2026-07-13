"""MCP tools for read-only database schema introspection.

Thin wrappers over :class:`~peek.services.schema_service`. They resolve an
alias, call the service, and return its credential-free models unchanged.
Denylisted tables are never revealed -- that is enforced in the service.
"""

from typing import List, Optional

from fastmcp import Context, FastMCP
from fastmcp.exceptions import ToolError

from peek.errors import PeekError
from peek.models.schema import SchemaResult, TableList
from peek.tools.context import app_context


def list_tables(
    db: str, ctx: Context, schema: Optional[str] = None
) -> TableList:
    """List the tables and views in a database.

    Args:
        db: The alias of the database to introspect (see ``list_databases``).
        ctx: The FastMCP request context (injected).
        schema: An optional namespace; defaults to the database's default
            schema.

    Returns:
        A ``TableList`` naming each visible table and view with its kind, plus
        a ``hidden_count`` of objects withheld by the denylist.
    """
    try:
        return app_context(ctx).schema_service.list_tables(db, schema)
    except PeekError as error:
        raise ToolError(str(error)) from error


def get_schema(
    db: str,
    ctx: Context,
    tables: Optional[List[str]] = None,
    schema: Optional[str] = None,
    limit: Optional[int] = None,
    offset: int = 0,
) -> SchemaResult:
    """Describe the columns, primary key, and foreign keys of tables.

    Pass ``tables`` to fetch a specific set, or omit it and page through every
    table with ``limit``/``offset``.

    Args:
        db: The alias of the database to introspect (see ``list_databases``).
        ctx: The FastMCP request context (injected).
        tables: An optional explicit list of table or view names.
        schema: An optional namespace; defaults to the default schema.
        limit: The maximum number of tables to return when paginating.
        offset: The number of tables to skip when paginating.

    Returns:
        A ``SchemaResult`` with each selected table's structure, the total
        number of visible tables, and a ``hidden_count`` for the denylist.
    """
    try:
        return app_context(ctx).schema_service.get_schema(
            db, tables, schema, limit, offset
        )
    except PeekError as error:
        raise ToolError(str(error)) from error


def register(mcp: FastMCP) -> None:
    """Attach this module's tools to ``mcp``."""
    mcp.tool(list_tables)
    mcp.tool(get_schema)
