"""Read-only SQL safety guard.

The single source of truth for deciding whether a SQL statement is a safe,
read-only query. Every SQL execution path funnels through here (via
``sql_service``) before a database is touched, so this module must never permit
anything that could mutate data or schema.

The check is deliberately conservative: anything that cannot be proven to be a
single read-only ``SELECT`` is rejected. It complements — never replaces — the
read-only database role that provides the second, independent safety layer.
"""

from typing import Dict, Optional, Tuple, Type

import sqlglot
from sqlglot import exp
from sqlglot.errors import SqlglotError


class UnsafeSQLError(Exception):
    """Raised when a statement is not a single, read-only SELECT query.

    The message is safe to surface to a caller: it describes the violation
    without echoing connection strings or credentials.
    """


_ALLOWED_ROOTS: Tuple[Type[exp.Expression], ...] = (
    exp.Query,
    exp.Subquery,
)

_FORBIDDEN_NODES: Tuple[Type[exp.Expression], ...] = (
    exp.Insert,
    exp.Update,
    exp.Delete,
    exp.Merge,
    exp.Create,
    exp.Drop,
    exp.Alter,
    exp.TruncateTable,
    exp.Grant,
    exp.Copy,
    exp.Set,
    exp.Command,
)

_NODE_NAMES: Dict[Type[exp.Expression], str] = {
    exp.Insert: "INSERT",
    exp.Update: "UPDATE",
    exp.Delete: "DELETE",
    exp.Merge: "MERGE",
    exp.Create: "CREATE",
    exp.Drop: "DROP",
    exp.Alter: "ALTER",
    exp.TruncateTable: "TRUNCATE",
    exp.Grant: "GRANT",
    exp.Copy: "COPY",
    exp.Set: "SET",
    exp.Command: "non-SELECT/unsupported",
}


def _describe(node: exp.Expression) -> str:
    """Return a human-readable name for a statement node.

    Args:
        node: The expression whose kind should be described.

    Returns:
        A short, credential-free label such as ``"DELETE"``.
    """
    for node_type, name in _NODE_NAMES.items():
        if isinstance(node, node_type):
            return name
    return type(node).__name__.upper()


def ensure_read_only(
    sql: str, dialect: Optional[str] = None
) -> exp.Expression:
    """Validate that ``sql`` is a single read-only SELECT statement.

    Parses ``sql`` and rejects it unless it is exactly one statement whose root
    is a ``SELECT`` (or set operation / parenthesized query) and whose tree
    contains no data- or schema-modifying construct anywhere — including inside
    CTEs and subqueries.

    Args:
        sql: The SQL text to check.
        dialect: Optional ``sqlglot`` dialect name to parse with (for example
            ``"postgres"``). When ``None``, the generic dialect is used.

    Returns:
        The parsed root expression, so callers can reuse it without re-parsing.

    Raises:
        UnsafeSQLError: If ``sql`` is empty, unparseable, contains more than
            one statement, is not a SELECT, or contains a mutating construct.
    """
    try:
        statements = sqlglot.parse(sql, dialect=dialect)
    except SqlglotError as error:
        raise UnsafeSQLError(
            "Could not parse the statement; only well-formed read-only "
            "SELECT queries are allowed."
        ) from error

    parsed = [statement for statement in statements if statement is not None]

    if not parsed:
        raise UnsafeSQLError("No SQL statement was provided.")

    if len(parsed) > 1:
        raise UnsafeSQLError(
            "Multiple statements are not allowed; submit a single read-only "
            "SELECT query."
        )

    root = parsed[0]

    if not isinstance(root, _ALLOWED_ROOTS):
        raise UnsafeSQLError(
            f"Statement type '{_describe(root)}' is not allowed; only "
            "read-only SELECT queries are permitted."
        )

    forbidden = root.find(*_FORBIDDEN_NODES)
    if forbidden is not None:
        raise UnsafeSQLError(
            f"The statement contains a disallowed '{_describe(forbidden)}' "
            "operation; only read-only SELECT queries are permitted."
        )

    return root
