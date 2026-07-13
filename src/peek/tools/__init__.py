"""The thin, agent-facing MCP tool layer.

Each module wraps a service and exposes its own ``register``; :func:`register`
here attaches all of them, so the server (Phase 7) wires the whole tool layer
with a single call.
"""

from fastmcp import FastMCP

from peek.tools import databases, schema, sql


def register(mcp: FastMCP) -> None:
    """Attach every peek tool to ``mcp``."""
    databases.register(mcp)
    schema.register(mcp)
    sql.register(mcp)
