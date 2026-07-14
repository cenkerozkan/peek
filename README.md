# peek

A safe, multi-database, **read-only SQL MCP server**. It exposes database
introspection and query-execution tools over any SQLAlchemy-supported database, so an
outer agent (Claude Code, Copilot) can do NL→SQL itself and run the result safely.

**v1 has no internal LLM.** The stack is `FastMCP` + `SQLAlchemy` + `sqlglot`.

See [`CLAUDE.md`](CLAUDE.md) for the entry point and [`docs/`](docs/) for the settled
architecture, structure, decisions, and conventions.

## Install & launch

**Not yet published to PyPI** (see `docs/roadmap.md` Phase 9), so install from the
git repository. `uv` and `pipx` both accept a git URL anywhere they accept a
package name.

The distribution name is `peek-sql` (`peek` and `peek-mcp` were both already taken
by unrelated packages — see `docs/decisions.md` #14). The import package and the
console command are both still `peek`.

### From git

```sh
uv tool install git+https://github.com/cenkerozkan/peek
```

The MCP launch config points `uvx` at the same URL. `uvx` re-resolves from git on
every launch, so a push is picked up on the next client restart:

```json
{
  "command": "uvx",
  "args": ["--from", "git+https://github.com/cenkerozkan/peek", "peek"]
}
```

`pipx install git+https://github.com/cenkerozkan/peek` works the same way for a
persistent install.

### From a local checkout

To run uncommitted changes, install from the working tree instead:

```sh
uv sync      # creates .venv, dev group included
uv run peek  # starts on stdio and waits silently
```

```json
{
  "command": "uv",
  "args": ["run", "--directory", "/path/to/peek", "peek"]
}
```

### Database drivers

Drivers are optional extras — install only the ones you connect to (see
`docs/decisions.md` #13). SQLite needs none; it uses the stdlib `sqlite3`.

The extra hangs off the distribution name, so a git install needs the PEP 508
form:

```sh
uv tool install "peek-sql[postgres] @ git+https://github.com/cenkerozkan/peek"
pipx install "peek-sql[postgres,mysql] @ git+https://github.com/cenkerozkan/peek"
```

### Connection registry

The server reads its alias → connection-string registry from
`databases.toml` in the platform's user config directory
(`~/Library/Application Support/peek` on macOS, `%LOCALAPPDATA%\peek` on Windows),
or from the path in `PEEK_CONFIG_FILE`. It exits with a `ConfigError` if the file
is missing, which an MCP client reports as a failure to start.

```toml
[databases.demo]
url = "sqlite:////absolute/path/to/demo.db"

[databases.prod]
url = "postgresql+psycopg://readonly_user:pw@host:5432/mydb"
exclude_tables = ["auth.sessions"]
```

Credentials live only in this file — never in the repo or the MCP launch config.

### Once published

```json
{
  "command": "uvx",
  "args": ["--from", "peek-sql", "peek"]
}
```

`pipx install peek-sql` and `python -m peek` will also work.

## Safety model

Two independent layers, neither of which may be weakened or bypassed:

- A read-only database role / grants.
- A client-side `sqlglot` parse check that rejects any non-`SELECT` statement before
  execution.

Connection strings never leave the server process: no tool return value or error
message ever contains one — callers see only database aliases.
