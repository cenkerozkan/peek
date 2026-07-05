"""Read-only SQL execution — the single chokepoint every query passes.

No SQL reaches a database except through :class:`SqlService`. It parses each
statement with the safety guard (rejecting anything that is not a single
read-only ``SELECT``), rejects any query that references a denylisted table,
then executes read-only and caps the result. It complements — never replaces —
the read-only database role that is the second, independent safety layer.

Credential isolation holds throughout: no return value or error message ever
contains a connection string (see `docs/architecture.md` -> "Credential
isolation").
"""

import datetime
import decimal
import uuid
from typing import Any, List

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlglot import exp

from src.peek.errors import QueryError
from src.peek.models.query import QueryResult
from src.peek.safety.guard import UnsafeSQLError, ensure_read_only
from src.peek.services.connection_registry import ConnectionRegistry


class ExcludedTableError(UnsafeSQLError):
    """Raised when a query references a table on the alias's denylist.

    Subclasses :class:`UnsafeSQLError` so a caller can catch a single type for
    every reason a query is refused. The message names only that a table is not
    permitted -- never the schema, the denylist, or any credential.
    """


class SqlService:
    """Validates and executes read-only queries against registered engines."""

    def __init__(self, registry: ConnectionRegistry, max_rows: int) -> None:
        self._registry = registry
        self._max_rows = max_rows

    def validate(self, alias: str, sql: str) -> exp.Expression:
        """Prove ``sql`` is a read-only query that touches no denied table.

        Args:
            alias: The database alias the query would run against.
            sql: The SQL text to check.

        Returns:
            The parsed root expression, so :meth:`execute` need not re-parse.

        Raises:
            RegistryError: If ``alias`` is not registered.
            UnsafeSQLError: If ``sql`` is not a single read-only SELECT.
            ExcludedTableError: If ``sql`` references a denylisted table.
        """
        dialect = self._registry.sqlglot_dialect(alias)
        root = ensure_read_only(sql, dialect)
        self._reject_excluded(alias, root)
        return root

    def execute(self, alias: str, sql: str) -> QueryResult:
        """Validate ``sql``, run it read-only, and return capped rows.

        Args:
            alias: The database alias to query.
            sql: The read-only SELECT to execute.

        Returns:
            A ``QueryResult`` whose rows are capped at the configured row
            limit, with ``truncated`` set when more rows were available.

        Raises:
            RegistryError: If ``alias`` is not registered.
            UnsafeSQLError: If ``sql`` is not a single read-only SELECT.
            ExcludedTableError: If ``sql`` references a denylisted table.
            QueryError: If the database fails to execute the query.
        """
        self.validate(alias, sql)
        engine = self._registry.get_engine(alias)
        try:
            with engine.connect() as connection:
                result = connection.execute(text(sql))
                columns = list(result.keys())
                fetched = result.fetchmany(self._max_rows + 1)
        except SQLAlchemyError as error:
            raise QueryError(
                f"Could not execute the query on database: {alias}"
            ) from error

        truncated = len(fetched) > self._max_rows
        kept = fetched[: self._max_rows]
        rows = [[self._coerce(value) for value in row] for row in kept]
        return QueryResult(
            alias=alias,
            columns=columns,
            rows=rows,
            row_count=len(rows),
            truncated=truncated,
        )

    def _reject_excluded(self, alias: str, root: exp.Expression) -> None:
        for table in root.find_all(exp.Table):
            if self._registry.is_excluded(alias, table.name, table.db or None):
                raise ExcludedTableError(
                    "The query references a table that is not permitted."
                )

    @staticmethod
    def _coerce(value: Any) -> Any:
        if value is None or isinstance(value, (bool, int, float, str)):
            return value
        if isinstance(value, (bytes, bytearray, memoryview)):
            return f"<binary: {len(bytes(value))} bytes>"
        if isinstance(
            value, (datetime.datetime, datetime.date, datetime.time)
        ):
            return value.isoformat()
        if isinstance(value, (decimal.Decimal, uuid.UUID)):
            return str(value)
        return str(value)


__all__: List[str] = ["ExcludedTableError", "SqlService"]
