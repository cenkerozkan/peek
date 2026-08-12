"""CLI entry point for the ``peek`` console command.

``click`` and ``tomlkit`` are direct dependencies (see pyproject.toml).
Bare ``peek`` (no subcommand) starts the MCP stdio server; ``peek --version``
shows the package version without loading SQLAlchemy or FastMCP.
"""

import sys

import click

from peek import __version__


@click.group(invoke_without_command=True)
@click.version_option(version=__version__, prog_name="peek")
@click.pass_context
def main(ctx: click.Context) -> None:
    """Safe, multi-database, read-only SQL and NoSQL MCP server.

    ``peek`` without subcommands starts the MCP stdio server.
    Subcommands (init, db) arrive in later tasks.
    """
    if ctx.invoked_subcommand is None:
        # Lazy-import to avoid loading SQLAlchemy/FastMCP for bare
        # invocations like ``peek --version`` or ``peek help``.
        from peek.server import build_server

        # Stdout is the MCP channel — do not print anything to it.
        build_server().run(transport="stdio", show_banner=False)


if __name__ == "__main__":
    main()
