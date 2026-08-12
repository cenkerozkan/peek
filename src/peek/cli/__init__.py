"""CLI entry point for the ``peek`` console command.

``click`` and ``tomlkit`` are direct dependencies (see pyproject.toml).
Bare ``peek`` (no subcommand) starts the MCP stdio server; ``peek --version``
shows the package version without loading SQLAlchemy or FastMCP.
"""

import os
from pathlib import Path
from typing import Optional

import click
from platformdirs import user_config_dir

from peek import __version__
from peek.cli.db import db
from peek.cli.init_cmd import init

_LOCAL_CONFIG = Path(".peek") / "databases.toml"


def resolve_config_path() -> Path:
    """Return the path to the databases.toml file the CLI should use.

    Search order:
    1. ``PEEK_CONFIG_FILE`` environment variable (consistent with server).
    2. ``.peek/databases.toml`` relative to the current working directory.
    3. Platform config directory via ``platformdirs``.
    4. Falls back to step 2 so error messages point the user at ``peek init``.

    Returns:
        The first path that exists, or the cwd-local default if nothing
        exists anywhere.
    """
    env_path: Optional[Path] = None
    env_var = os.environ.get("PEEK_CONFIG_FILE")
    if env_var is not None:
        env_path = Path(env_var)
        if env_path.exists():
            return env_path

    local_path = Path.cwd() / _LOCAL_CONFIG
    if local_path.exists():
        return local_path

    platform_dir = user_config_dir("peek")
    if platform_dir is not None:
        platform_path = Path(platform_dir) / "databases.toml"
        if platform_path.exists():
            return platform_path

    return local_path


@click.group(invoke_without_command=True)
@click.version_option(version=__version__, prog_name="peek")
@click.pass_context
def main(ctx: click.Context) -> None:
    """Safe, multi-database, read-only SQL and NoSQL MCP server.

    ``peek`` without subcommands starts the MCP stdio server.
    Subcommands (init, db) arrive in later tasks.
    """
    if ctx.invoked_subcommand is None:
        from peek.server import build_server

        build_server().run(transport="stdio", show_banner=False)


main.add_command(init, "init")
main.add_command(db, "db")

if __name__ == "__main__":
    main()
