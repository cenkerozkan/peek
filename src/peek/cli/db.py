"""``peek db`` — manage database connections for peek."""

from typing import List, Optional

import click
from pydantic import SecretStr

from peek.cli.checks import require_config
from peek.errors import ConfigError, RegistryError
from peek.infra.config_file import load_registry, remove_entry, save_entry
from peek.models.config import DatabaseEntry
from peek.services.connection_registry import ConnectionRegistry


@click.group()
def db() -> None:
    """Manage database connections for peek."""
    pass


@db.command()
def add() -> None:
    """Add a new database connection interactively.

    Prompts for alias, connection URL, dialect override, and
    excluded tables. Validates the connection before persisting.
    """
    path = require_config()

    click.echo(
        "Register a new database connection.\n"
        "Example:\n"
        "  Alias:            prod\n"
        "  Connection URL:   postgresql+psycopg://readonly@db.internal:5432/app\n"
        "  Dialect override: (leave blank for auto-detect)\n"
        "  Excluded tables:  users, payment_methods\n",
        err=True,
    )
    alias: str = click.prompt(
        'Alias (short name your agent will use, e.g. "prod")',
        err=True,
    )

    while not alias.strip():
        click.echo("Alias must not be empty.", err=True)
        alias = click.prompt(
            'Alias (short name your agent will use, e.g. "prod")',
            err=True,
        )

    url: str = click.prompt(
        "Connection URL (SQLAlchemy URL, e.g. "
        '"postgresql+psycopg://user:pass@host/db" '
        'or "sqlite:///path/to/file.db")',
        err=True,
    )

    dialect_raw: str = click.prompt(
        "Dialect override (leave blank unless auto-detect picks "
        "the wrong SQL dialect)",
        default="",
        show_default=False,
        err=True,
    )
    if not dialect_raw.strip():
        dialect: Optional[str] = None
    else:
        dialect = dialect_raw

    excludes_raw: str = click.prompt(
        "Excluded tables (comma-separated) "
        '(tables the agent must never see, e.g. "users, sessions")',
        default="",
        show_default=False,
        err=True,
    )
    excluded_tables: List[str] = (
        [t.strip() for t in excludes_raw.split(",") if t.strip()]
        if excludes_raw.strip()
        else []
    )

    entry = DatabaseEntry(
        url=SecretStr(url),
        dialect=dialect,
        exclude_tables=excluded_tables,
    )

    try:
        registry = ConnectionRegistry()
        registry.add(alias, entry)
        registry.remove(alias)
    except RegistryError as error:
        click.echo(str(error), err=True)
        raise SystemExit(1) from None

    save_entry(path, alias, entry)

    click.echo(
        f"Database '{alias}' added.\n"
        "Restart the MCP server for changes to take effect.",
        err=True,
    )


@db.command()
def remove() -> None:
    """Remove a database connection from the config file.

    The database is unregistered from databases.toml. No data is deleted.
    Restart the MCP server afterwards for the change to take effect.
    """
    path = require_config()

    try:
        registry = load_registry(path)
    except ConfigError:
        click.echo(
            "No databases configured. Run 'peek db add'.",
            err=True,
        )
        raise SystemExit(1) from None

    aliases = list(registry.keys())
    click.echo("Available database aliases:", err=True)
    for alias in aliases:
        click.echo(f"  - {alias}", err=True)

    alias = click.prompt("Alias to remove", err=True)

    try:
        remove_entry(path, alias)
    except ConfigError as error:
        click.echo(str(error), err=True)
        raise SystemExit(1) from None

    click.echo(
        f"Database '{alias}' removed.\n"
        "Restart the MCP server for changes to take effect.",
        err=True,
    )


@db.command("list")
def list_() -> None:
    """List all configured database aliases and their dialects.

    Shows every database registered in the active databases.toml file.
    """
    path = require_config()

    try:
        registry = load_registry(path)
    except ConfigError:
        click.echo(
            "No databases configured. Run 'peek db add'.",
            err=True,
        )
        raise SystemExit(1) from None

    header = f"{'ALIAS':<20} {'DIALECT':<10}"
    separator = "-" * len(header)
    click.echo(header, err=True)
    click.echo(separator, err=True)

    for alias, entry in registry.items():
        dialect = entry.dialect if entry.dialect else "auto"
        click.echo(f"{alias:<20} {dialect:<10}", err=True)
