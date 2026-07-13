"""Pydantic model describing the result of a read-only query.

This is the credential-free I/O type returned by
:mod:`peek.services.sql_service`. It never carries a connection string or
other credential material. Rows are positional arrays aligned to ``columns`` so
column names are not repeated for every row.
"""

from typing import Any, List, Optional

from pydantic import BaseModel, ConfigDict


class ValidationResult(BaseModel):
    """The verdict on whether a query is a safe, read-only statement.

    Returned by the ``validate_sql`` tool instead of raising, so an agent can
    check a query before running it. ``message`` explains why an invalid query
    was refused; it is credential-safe and never echoes the submitted SQL.

    Attributes:
        alias: The database alias the query was checked against.
        valid: Whether the query is a single read-only ``SELECT`` that touches
            no denied table.
        message: The reason the query was refused, or ``None`` when valid.
    """

    model_config = ConfigDict(extra="forbid")

    alias: str
    valid: bool
    message: Optional[str] = None


class QueryResult(BaseModel):
    """The rows a read-only query returned, capped to a row limit.

    Attributes:
        alias: The database alias the query ran against.
        columns: The result column names, in order.
        rows: The result rows as positional values aligned to ``columns``.
            Values are coerced to JSON-safe primitives.
        row_count: The number of rows returned (after any truncation).
        truncated: Whether more rows were available than the row cap allowed.
    """

    model_config = ConfigDict(extra="forbid")

    alias: str
    columns: List[str]
    rows: List[List[Any]]
    row_count: int
    truncated: bool
