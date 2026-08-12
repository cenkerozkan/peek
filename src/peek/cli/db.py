"""``peek db`` — manage database connections for peek."""

from typing import List, Optional

import click
from pydantic import SecretStr

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
    alias: str = click.prompt("Alias", err=True)

    while not alias.strip():
        click.echo("Alias must not be empty.", err=True)
        alias = click.prompt("Alias", err=True)

    url: str = click.prompt("Connection URL", err=True)

    dialect_raw: str = click.prompt(
        "Dialect override", default="", show_default=False, err=True
    )
    if not dialect_raw.strip():
        dialect: Optional[str] = None
    else:
        dialect = dialect_raw

    excludes_raw: str = click.prompt(
        "Excluded tables (comma-separated)",
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

    from peek.cli import resolve_config_path

    path = resolve_config_path()
    save_entry(path, alias, entry)

    click.echo(
        f"Database '{alias}' added.\n"
        "Restart the MCP server for changes to take effect.",
        err=True,
    )


@db.command()
def remove() -> None:
    """Remove a database connection from the registry.

    Shows the available aliases and prompts the user to pick one
    for removal. No connection is opened — this is a file operation.
    """
    from peek.cli import resolve_config_path

    path = resolve_config_path()

    if not path.is_file():
        click.echo(
            "No config file found. Run 'peek init' first.",
            err=True,
        )
        raise SystemExit(1) from None

    try:
        registry = load_registry(path)
    except ConfigError:
        click.echo(
            "No config file found. Run 'peek init' first.",
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
