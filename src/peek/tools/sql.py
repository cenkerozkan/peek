"""MCP tools for validating and running read-only SQL.

Thin wrappers over :class:`~src.peek.services.sql_service`, the single safety
chokepoint. ``validate_sql`` reports a verdict instead of raising, so an agent
can check a query first; ``run_sql`` executes and returns capped rows. No SQL
reaches a database except through the service.
"""

from fastmcp import Context, FastMCP
from fastmcp.exceptions import ToolError

from src.peek.errors import PeekError
from src.peek.models.query import QueryResult, ValidationResult
from src.peek.safety.guard import UnsafeSQLError
from src.peek.tools.context import app_context


def validate_sql(db: str, ctx: Context, sql: str) -> ValidationResult:
    """Check whether a query is a safe, read-only statement, without running.

    Use this before ``run_sql`` to confirm a query is a single read-only
    ``SELECT`` that touches no denied table. A refused query is a verdict, not
    an error: the result's ``valid`` is ``False`` and ``message`` says why.

    Args:
        db: The database alias to check against (see ``list_databases``).
        ctx: The FastMCP request context (injected).
        sql: The SQL text to validate.

    Returns:
        A ``ValidationResult`` whose ``valid`` flag reports the verdict.
    """
    try:
        app_context(ctx).sql_service.validate(db, sql)
    except UnsafeSQLError as error:
        return ValidationResult(alias=db, valid=False, message=str(error))
    except PeekError as error:
        raise ToolError(str(error)) from error
    return ValidationResult(alias=db, valid=True, message=None)


def run_sql(db: str, ctx: Context, sql: str) -> QueryResult:
    """Run a read-only query and return its rows, capped to a row limit.

    The query is validated first; anything that is not a single read-only
    ``SELECT``, or that touches a denied table, is refused before execution.

    Args:
        db: The alias of the database to query (see ``list_databases``).
        ctx: The FastMCP request context (injected).
        sql: The read-only ``SELECT`` to run.

    Returns:
        A ``QueryResult`` with the columns and rows, ``truncated`` set when
        more rows were available than the row cap allowed.
    """
    try:
        return app_context(ctx).sql_service.execute(db, sql)
    except (PeekError, UnsafeSQLError) as error:
        raise ToolError(str(error)) from error


def register(mcp: FastMCP) -> None:
    """Attach this module's tools to ``mcp``."""
    mcp.tool(validate_sql)
    mcp.tool(run_sql)
