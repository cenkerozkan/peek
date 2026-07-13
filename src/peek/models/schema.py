"""Pydantic models describing introspected database schemas.

These are the credential-free I/O types returned by
:mod:`peek.services.schema_service`. They never carry a connection
string or other credential material.
"""

from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict

Kind = Literal["table", "view"]


class ForeignKey(BaseModel):
    """A foreign-key relationship from one table to another.

    Attributes:
        columns: The constrained columns on the owning table.
        references_table: The table the foreign key points at.
        references_columns: The referenced columns on that table.
    """

    model_config = ConfigDict(extra="forbid")

    columns: List[str]
    references_table: str
    references_columns: List[str]


class Column(BaseModel):
    """A single column in a table or view.

    Attributes:
        name: The column name.
        type: The dialect-native type rendered as a string.
        nullable: Whether the column accepts ``NULL``.
        default: The column's server default, if any.
        primary_key: Whether the column is part of the primary key.
    """

    model_config = ConfigDict(extra="forbid")

    name: str
    type: str
    nullable: bool
    default: Optional[str] = None
    primary_key: bool = False


class TableInfo(BaseModel):
    """A table or view name paired with its kind.

    Attributes:
        name: The table or view name.
        kind: Whether the object is a ``table`` or a ``view``.
    """

    model_config = ConfigDict(extra="forbid")

    name: str
    kind: Kind


class TableSchema(BaseModel):
    """The introspected structure of a single table or view.

    Attributes:
        name: The table or view name.
        kind: Whether the object is a ``table`` or a ``view``.
        columns: The ordered columns.
        primary_key: The columns forming the primary key, if any.
        foreign_keys: The foreign-key relationships, if any.
    """

    model_config = ConfigDict(extra="forbid")

    name: str
    kind: Kind
    columns: List[Column]
    primary_key: List[str]
    foreign_keys: List[ForeignKey]


class TableList(BaseModel):
    """The result of listing the tables and views in a database.

    Attributes:
        alias: The database alias the listing came from.
        schema_name: The namespace inspected, if a non-default one was given.
        tables: The visible tables and views, each tagged with its kind.
        hidden_count: How many tables and views were withheld by the
            denylist. Their names are never disclosed, but the count lets a
            caller know some data is out of reach and may be worth asking a
            human about.
    """

    model_config = ConfigDict(extra="forbid")

    alias: str
    schema_name: Optional[str] = None
    tables: List[TableInfo]
    hidden_count: int


class SchemaResult(BaseModel):
    """The result of introspecting one or more tables' schemas.

    Attributes:
        alias: The database alias the schema came from.
        schema_name: The namespace inspected, if a non-default one was given.
        tables: The introspected tables and views.
        total_tables: The total number of visible tables in scope, so a
            caller can tell whether a paginated request left more behind.
        truncated: Whether a ``limit``/``offset`` page stopped short of the
            full set of visible tables in scope.
        hidden_count: How many tables and views were withheld by the
            denylist. Their names are never disclosed, but the count lets a
            caller know some data is out of reach and may be worth asking a
            human about.
    """

    model_config = ConfigDict(extra="forbid")

    alias: str
    schema_name: Optional[str] = None
    tables: List[TableSchema]
    total_tables: int
    truncated: bool
    hidden_count: int
