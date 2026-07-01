# nl2sql

A safe, multi-database, **read-only SQL MCP server**. It exposes database
introspection and query-execution tools over any SQLAlchemy-supported database, so an
outer agent (Claude Code, Copilot) can do NL→SQL itself and run the result safely.

**v1 has no internal LLM.** The stack is `FastMCP` + `SQLAlchemy` + `sqlglot`.

See [`CLAUDE.md`](CLAUDE.md) for the entry point and [`docs/`](docs/) for the settled
architecture, structure, decisions, and conventions.

## Safety model

Two independent layers, neither of which may be weakened or bypassed:

- A read-only database role / grants.
- A client-side `sqlglot` parse check that rejects any non-`SELECT` statement before
  execution.

Connection strings never leave the server process: no tool return value or error
message ever contains one — callers see only database aliases.
