# peek

A safe, multi-database, **read-only SQL MCP server**. It exposes database
introspection and query-execution tools over any SQLAlchemy-supported database, so an
outer agent (Claude Code, Copilot) can do NL→SQL itself and run the result safely.

**v1 has no internal LLM.** The stack is `FastMCP` + `SQLAlchemy` + `sqlglot`.

See [`CLAUDE.md`](CLAUDE.md) for the entry point and [`docs/`](docs/) for the settled
architecture, structure, decisions, and conventions.

## Install & launch

**Not yet published to PyPI** — the packaging is done and verified locally, but
`peek-sql` 0.1.0 has not been published yet (see `docs/roadmap.md` Phase 9). The
commands below describe the intended install story for once it is.

The distribution name on PyPI is `peek-sql` (`peek` and `peek-mcp` were both
already taken by unrelated packages — see `docs/decisions.md` #14). The import
package and the console command are both still `peek`.

Once published, the primary path is `uvx`, matching the MCP ecosystem's
launch-config convention:

```json
{
  "command": "uvx",
  "args": ["--from", "peek-sql", "peek"]
}
```

`pipx` is a supported alternative for a persistent install:

```sh
pipx install peek-sql
```

Database drivers are optional extras — install only the ones you connect to
(see `docs/decisions.md` #13):

```sh
uvx --from 'peek-sql[postgres]' peek
pipx install 'peek-sql[postgres,mysql]'
```

`python -m peek` also works if you've installed the package yourself.

## Safety model

Two independent layers, neither of which may be weakened or bypassed:

- A read-only database role / grants.
- A client-side `sqlglot` parse check that rejects any non-`SELECT` statement before
  execution.

Connection strings never leave the server process: no tool return value or error
message ever contains one — callers see only database aliases.
