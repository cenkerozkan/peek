"""CLI entry point for the ``peek`` console command.

``click`` and ``tomlkit`` are direct dependencies (see pyproject.toml).
Bare ``peek`` (no subcommand) starts the MCP stdio server; ``peek --version``
shows the package version without loading SQLAlchemy or FastMCP.
"""

import click

from peek import __version__
from peek.cli.db import db
from peek.cli.init_cmd import init


@click.group(invoke_without_command=True)
@click.version_option(version=__version__, prog_name="peek")
@click.pass_context
def main(ctx: click.Context) -> None:
    """Safe, multi-database, read-only SQL and NoSQL MCP server.

    Run without a subcommand to start the MCP stdio server.
    """
    if ctx.invoked_subcommand is None:
        from peek.server import build_server

        build_server().run(transport="stdio", show_banner=False)


main.add_command(init, "init")
main.add_command(db, "db")

if __name__ == "__main__":
    main()
