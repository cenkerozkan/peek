# peek

**Safe, multi-database, read-only SQL over MCP.**

`peek` is an [MCP](https://modelcontextprotocol.io) server that gives a coding
agent — Claude Code, Cursor, GitHub Copilot — the ability to explore your
databases and run queries against them, without the ability to change anything.

```
You:   which customers churned last quarter?
Agent: [list_databases] → [get_schema] → [run_sql] → answers from your real data
```

The agent writes the SQL itself. `peek`'s job is to make sure that whatever it
writes is safe to run, that it can reach every database you've registered by a
short alias, and that your connection strings never leave your machine.

**`peek` contains no LLM.** It is `FastMCP` + `SQLAlchemy` + `sqlglot`, and the
reasoning happens in the agent you already use.

## Table of contents

- [Why peek](#why-peek)
- [Safety model](#safety-model)
- [Quick start](#quick-start)
  - [CLI reference](#cli-reference)
- [Install](#install)
  - [Database drivers](#database-drivers)
- [Configure your databases](#configure-your-databases)
  - [CLI setup (recommended)](#cli-setup-recommended)
  - [Manual setup](#manual-setup)
  - [Config file location](#config-file-location)
- [Add peek to your editor](#add-peek-to-your-editor)
  - [Claude Code](#claude-code)
  - [Cursor](#cursor)
  - [VS Code (GitHub Copilot)](#vs-code-github-copilot)
- [Tools](#tools)
- [Settings](#settings)
- [Roadmap](#roadmap)
- [Development](#development)
- [Documentation](#documentation)
- [License](#license)

## Why peek

Handing an agent a database connection is the fast way to get answers out of
your data, and the fast way to lose it. The usual fixes are all unsatisfying:
paste the schema into the chat by hand, copy queries back and forth yourself, or
give the agent a live connection and hope.

`peek` takes the third path and removes the hope:

- **Read-only, enforced.** Every statement is parsed before it executes, and
  anything that is not a single read-only `SELECT` is refused. Not a prompt
  telling the model to behave — a parse check it cannot talk its way past.
- **Many databases, one server.** Register your warehouse, your staging replica,
  and a local SQLite file, and address each by alias. The agent discovers them at
  runtime; you don't rewire anything.
- **Your credentials stay put.** Connection strings live in a local config file
  and are never returned by a tool, never appear in an error, and never reach the
  model — and therefore never reach a model provider's API. The agent sees only
  aliases like `prod` and `analytics`.
- **Hide what shouldn't be seen.** A per-database denylist keeps tables out of
  the agent's context entirely — they don't appear in schema listings and queries
  against them are refused.

## Safety model

Two independent layers. Neither substitutes for the other, and neither may be
weakened or bypassed:

1. **A read-only database role.** Grant `peek`'s user `SELECT` and nothing else.
   This is your real guarantee, enforced by the database itself.
2. **A client-side parse check.** Before execution, `sqlglot` parses the
   statement in the database's own dialect. Anything that is not a single
   read-only `SELECT` — an `INSERT`, a `DROP`, a second statement smuggled in
   after a semicolon, a CTE wrapping a write — is refused before it reaches the
   connection.

On top of both, **credential isolation**: no tool return value and no error
message ever contains a connection string. `list_databases` returns aliases only.

> SQLite has no role system, so layer 1 is unavailable there and you are relying
> on the parse check alone. Fine for local exploration; think twice before
> pointing it at anything you'd miss.

## Install

`peek` is published as **`peek-db`** (the names `peek` and `peek-mcp` were
already taken on PyPI). The command and the import package are both `peek`.

You don't need to install it explicitly — the editor configs below run it with
`uvx`, which fetches and caches it on first launch. To install it anyway:

```sh
uv tool install peek-db
```

or

```sh
pipx install peek-db
```

Requires Python 3.13+.

### Database drivers

SQLAlchemy ships dialects, not drivers, so each backend needs its connector.
Install only the ones you actually connect to:

| Backend    | Extra          | Driver          |
| ---------- | -------------- | --------------- |
| SQLite     | *(none)*       | stdlib `sqlite3` |
| PostgreSQL | `postgres`     | `psycopg`       |
| MySQL      | `mysql`        | `pymysql`       |
| MariaDB    | `mysql`        | `pymysql`       |
| SQL Server | `mssql`        | `pyodbc`        |
| Oracle     | `oracle`       | `oracledb`      |
|            | `all-drivers`  | all of the above |

```sh
uv tool install 'peek-db[postgres]'
pipx install 'peek-db[postgres,mysql]'
```

In an editor config, put the extra in the `--from` argument:

```json
{ "command": "uvx", "args": ["--from", "peek-db[postgres]", "peek"] }
```

## Quick start

```sh
peek init            # creates .peek/databases.toml in the current directory
peek db add          # prompts for alias, URL, dialect, and excluded tables
```

Then add `peek` to your editor (see below).

### CLI reference

| Command           | What it does                                     |
| ----------------- | ------------------------------------------------ |
| `peek`            | Start the MCP stdio server                       |
| `peek --version`  | Show the installed version                       |
| `peek init`       | Create a `.peek/` config directory               |
| `peek db add`     | Add a database connection interactively          |
| `peek db remove`  | Remove a database connection                     |
| `peek db list`    | List configured databases and their dialects     |

## Configure your databases

`peek` reads an alias → connection-string registry from a TOML file. **This file
is the only place your credentials live** — not in the repo, not in the editor
config, not in the agent's context.

### CLI setup (recommended)

The easiest way to register a database is with the interactive CLI:

```sh
peek init            # creates a .peek/ directory with a databases.toml template
peek db add          # prompts for alias, URL, dialect, and excluded tables
peek db list         # shows what's registered
peek db remove       # removes an entry
```

`peek init` creates `.peek/databases.toml` in the current project directory.
The `.peek/` directory is automatically added to `.gitignore` (it holds
credentials).

### Manual setup

You can also edit `.peek/databases.toml` directly. The TOML structure is:

```toml
# A local SQLite file. Note the four slashes for an absolute path.
[databases.demo]
url = "sqlite:////Users/you/data/demo.db"

# A production replica, reached through a read-only role.
[databases.prod]
url = "postgresql+psycopg://readonly_user:secret@db.internal:5432/app"
exclude_tables = ["users", "auth.sessions", "payment_methods"]

[databases.warehouse]
url = "mysql+pymysql://analyst:secret@warehouse.internal:3306/facts"
```

Each entry takes:

- **`url`** *(required)* — a [SQLAlchemy connection
  URL](https://docs.sqlalchemy.org/en/20/core/engines.html#database-urls).
  Use the credentials of a role that can only `SELECT`.
- **`exclude_tables`** *(optional)* — tables the agent must never see. A bare
  name (`users`) matches that table in any schema; a qualified name
  (`auth.sessions`) matches only that one. Matching is case-insensitive. Excluded
  tables are absent from schema listings, and queries touching them are refused.
- **`dialect`** *(optional)* — a `sqlglot` dialect override, for the rare backend
  whose SQLAlchemy dialect name doesn't map cleanly.

If this file is missing, `peek` exits at startup — which your editor will report
as the server failing to start.

### Config file location

`peek` resolves the config file in this order:

1. `PEEK_CONFIG_FILE` environment variable, if set
2. `.peek/databases.toml` in the current directory
3. `databases.toml` in the platform user config directory:

| OS      | Path                                          |
| ------- | --------------------------------------------- |
| macOS   | `~/Library/Application Support/peek/databases.toml` |
| Linux   | `~/.config/peek/databases.toml`                |
| Windows | `%LOCALAPPDATA%\peek\databases.toml`           |

You can always point `PEEK_CONFIG_FILE` at a custom location.

## Add peek to your editor

Every editor below launches the same command. If you installed with `uv tool` or
`pipx`, you can replace the `uvx` command with a bare `peek`.

### Claude Code

```sh
claude mcp add peek -- uvx --from peek-db peek
```

Add `-s user` to make it available in every project rather than just this one,
and use `--env` if your registry lives somewhere non-default:

```sh
claude mcp add peek -s user --env PEEK_CONFIG_FILE=/path/to/databases.toml -- uvx --from peek-db peek
```

Verify with `/mcp` inside Claude Code — `peek` should be listed as connected,
with five tools.

### Cursor

Create `.cursor/mcp.json` in your project (or `~/.cursor/mcp.json` for every
project):

```json
{
  "mcpServers": {
    "peek": {
      "command": "uvx",
      "args": ["--from", "peek-db", "peek"]
    }
  }
}
```

Then enable `peek` under **Settings → MCP**.

### VS Code (GitHub Copilot)

Create `.vscode/mcp.json` in your project:

```json
{
  "servers": {
    "peek": {
      "type": "stdio",
      "command": "uvx",
      "args": ["--from", "peek-db", "peek"]
    }
  }
}
```

Open Copilot Chat, switch to **Agent** mode, and `peek`'s tools appear in the
tool picker. For a global install instead, run **MCP: Open User Configuration**
from the Command Palette and add the same `servers` block there.

## Tools

| Tool             | What it does                                                                 |
| ---------------- | ---------------------------------------------------------------------------- |
| `list_databases` | Lists every registered database by alias and dialect. Credential-free — call this first. |
| `list_tables`    | Lists the tables and views in a database, with a count of any withheld by the denylist. |
| `get_schema`     | Describes columns, primary keys, and foreign keys — for named tables, or paged through all of them. |
| `validate_sql`   | Checks a query is a safe read-only `SELECT` **without running it**. Returns a verdict, not an error. |
| `run_sql`        | Validates, then runs a read-only query and returns rows, capped at a row limit. |

Every tool takes a `db` argument — the alias from `list_databases`.

## Settings

Environment variables, all prefixed `PEEK_`:

| Variable           | Default                              | Meaning                              |
| ------------------ | ------------------------------------ | ------------------------------------ |
| `PEEK_CONFIG_FILE` | `databases.toml` in the user config dir | Path to the connection registry.  |
| `PEEK_MAX_ROWS`    | `1000`                               | Row cap applied by `run_sql`. Results beyond it are truncated, and `truncated` is set on the response. |

## Roadmap

**MongoDB support is next.** `peek` is becoming a read-only *database* server, not
just a read-only *SQL* server — which is why the package is `peek-db` and not
`peek-sql`.

Two things will change when it lands, and they're worth knowing before you build on
this:

- **`run_sql`/`validate_sql` become `run_query`/`validate_query`.** One tool surface
  for every backend; the alias you pass decides the query language, and
  `list_databases` tells you which one it speaks.
- **Read-only means something different for Mongo.** There's no SQL to parse, so the
  guard becomes an operation allowlist (`find`, `aggregate`, `count`, `distinct`).
  Note that an aggregation pipeline is *not* inherently read-only — `$out` and
  `$merge` write, and `$out` will replace an entire collection — so pipelines are
  walked stage by stage and refused if they contain one.

See [`docs/roadmap.md`](docs/roadmap.md) Phases 10–11 and
[`docs/decisions.md`](docs/decisions.md) #20–#22.

## Development

```sh
git clone https://github.com/cenkerozkan/peek
cd peek
uv sync          # installs the package and the dev tooling
uv run pytest    # the suite runs against temporary SQLite databases
uv run peek      # starts on stdio and waits silently — that's a healthy server
```

To point an editor at your working tree instead of the published package:

```json
{
  "command": "uv",
  "args": ["run", "--directory", "/path/to/peek", "peek"]
}
```

Linting and formatting run through `pre-commit` (`ruff`, `isort`, `ty`):

```sh
uv run pre-commit install
uv run pre-commit run --all-files
```

## Documentation

| Topic                                    | File                   |
| ---------------------------------------- | ---------------------- |
| Architecture: layers, interfaces, safety | `docs/architecture.md` |
| Repo / package structure & layer rules   | `docs/structure.md`    |
| Decision log (what we chose, and why)    | `docs/decisions.md`    |
| Killed / suspended ideas                 | `docs/backlog.md`      |
| Code conventions                         | `docs/conventions.md`  |
| Roadmap                                  | `docs/roadmap.md`      |
| Testing & installation from TestPyPI     | `docs/testing-installation.md` |

[`CLAUDE.md`](CLAUDE.md) is the entry point for AI agents working on this repo.

## License

MIT — see [`LICENSE`](LICENSE).
