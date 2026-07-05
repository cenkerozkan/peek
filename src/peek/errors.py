"""Shared exception hierarchy for the peek server.

All project-specific exceptions derive from :class:`PeekError` so callers
can catch the whole family with one `except` clause. Messages raised from
these exceptions must never contain connection strings or other credential
material — see the credential-isolation rule in `docs/architecture.md`.
"""


class PeekError(Exception):
    """Base class for all peek exceptions."""


class ConfigError(PeekError):
    """Raised when the config file or its contents are invalid."""


class RegistryError(PeekError):
    """Raised when a database cannot be resolved, connected to, or used.

    The message names only the database alias, never the connection string.
    """


class SchemaError(PeekError):
    """Raised when a database's schema cannot be introspected.

    The message names only the database alias (and table, if relevant),
    never the connection string.
    """


class QueryError(PeekError):
    """Raised when a read-only query cannot be executed.

    Wraps the underlying database error so the message names only the
    database alias, never the connection string or SQL parameters.
    """
