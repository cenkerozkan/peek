"""Read-only schema introspection over registered database engines.

Resolves an alias to its validated engine via the
:class:`~src.peek.services.connection_registry.ConnectionRegistry` and reads
structure with SQLAlchemy's inspector. No SQL is executed here, so this does
not route through the safety guard; it still obeys credential isolation --
connection strings never appear in a return value or an error message (see
`docs/architecture.md` -> "Credential isolation").
"""

from typing import Dict, List, Optional, Tuple

from sqlalchemy import inspect
from sqlalchemy.engine import Inspector
from sqlalchemy.exc import SQLAlchemyError

from src.peek.errors import SchemaError
from src.peek.models.schema import (
    Column,
    ForeignKey,
    Kind,
    SchemaResult,
    TableInfo,
    TableList,
    TableSchema,
)
from src.peek.services.connection_registry import ConnectionRegistry


class SchemaService:
    """Introspects tables, views, and columns for registered databases."""

    def __init__(self, registry: ConnectionRegistry) -> None:
        self._registry = registry

    def list_tables(
        self, alias: str, schema: Optional[str] = None
    ) -> TableList:
        """List every table and view in a database.

        Args:
            alias: The database alias to introspect.
            schema: An optional namespace; defaults to the database's
                default schema.

        Returns:
            A ``TableList`` naming each table and view with its kind.

        Raises:
            RegistryError: If ``alias`` is not registered.
            SchemaError: If the database's names cannot be read.
        """
        inspector = self._inspector(alias)
        infos, hidden = self._table_infos(inspector, alias, schema)
        return TableList(
            alias=alias,
            schema_name=schema,
            tables=infos,
            hidden_count=hidden,
        )

    def get_schema(
        self,
        alias: str,
        tables: Optional[List[str]] = None,
        schema: Optional[str] = None,
        limit: Optional[int] = None,
        offset: int = 0,
    ) -> SchemaResult:
        """Introspect the structure of some or all tables in a database.

        Pass ``tables`` to fetch a specific set (in the given order), or omit
        it and page through every table with ``limit``/``offset``.

        Args:
            alias: The database alias to introspect.
            tables: An optional explicit list of table or view names.
            schema: An optional namespace; defaults to the default schema.
            limit: The maximum number of tables to return when paginating.
                ``None`` returns every table from ``offset`` onward.
            offset: The number of tables to skip when paginating.

        Returns:
            A ``SchemaResult`` with the structured columns, primary key, and
            foreign keys of each selected table.

        Raises:
            RegistryError: If ``alias`` is not registered.
            SchemaError: If a requested table is unknown, the pagination
                bounds are negative, or the schema cannot be read.
        """
        inspector = self._inspector(alias)
        infos, hidden = self._table_infos(inspector, alias, schema)
        kinds: Dict[str, Kind] = {info.name: info.kind for info in infos}

        chosen, total, truncated = self._select(
            alias, kinds, tables, limit, offset
        )
        schemas = [
            self._reflect_table(inspector, alias, name, kinds[name], schema)
            for name in chosen
        ]
        return SchemaResult(
            alias=alias,
            schema_name=schema,
            tables=schemas,
            total_tables=total,
            truncated=truncated,
            hidden_count=hidden,
        )

    def _inspector(self, alias: str) -> Inspector:
        engine = self._registry.get_engine(alias)
        return inspect(engine)

    def _table_infos(
        self, inspector: Inspector, alias: str, schema: Optional[str]
    ) -> Tuple[List[TableInfo], int]:
        try:
            tables = sorted(inspector.get_table_names(schema=schema))
            views = sorted(inspector.get_view_names(schema=schema))
        except SQLAlchemyError as error:
            raise SchemaError(
                f"Could not read schema for database: {alias}"
            ) from error
        found = [TableInfo(name=name, kind="table") for name in tables] + [
            TableInfo(name=name, kind="view") for name in views
        ]
        visible = [
            info
            for info in found
            if not self._registry.is_excluded(alias, info.name, schema)
        ]
        return visible, len(found) - len(visible)

    def _select(
        self,
        alias: str,
        kinds: Dict[str, Kind],
        tables: Optional[List[str]],
        limit: Optional[int],
        offset: int,
    ) -> tuple[List[str], int, bool]:
        if tables is not None:
            for name in tables:
                if name not in kinds:
                    raise SchemaError(
                        f"Unknown table: {name} in database: {alias}"
                    )
            return list(tables), len(tables), False

        if offset < 0 or (limit is not None and limit < 0):
            raise SchemaError("limit and offset must be non-negative.")
        names = list(kinds)
        total = len(names)
        end = None if limit is None else offset + limit
        page = names[offset:end]
        return page, total, offset + len(page) < total

    def _reflect_table(
        self,
        inspector: Inspector,
        alias: str,
        name: str,
        kind: Kind,
        schema: Optional[str],
    ) -> TableSchema:
        try:
            raw_columns = inspector.get_columns(name, schema=schema)
            constraint = inspector.get_pk_constraint(name, schema=schema)
            raw_foreign_keys = inspector.get_foreign_keys(name, schema=schema)
        except SQLAlchemyError as error:
            raise SchemaError(
                f"Could not read schema for database: {alias}"
            ) from error

        primary_key = list(constraint.get("constrained_columns") or [])
        primary_key_set = set(primary_key)
        columns = [
            Column(
                name=column["name"],
                type=str(column["type"]),
                nullable=bool(column["nullable"]),
                default=self._render_default(column.get("default")),
                primary_key=column["name"] in primary_key_set,
            )
            for column in raw_columns
        ]
        foreign_keys = [
            ForeignKey(
                columns=list(foreign_key["constrained_columns"]),
                references_table=foreign_key["referred_table"],
                references_columns=list(foreign_key["referred_columns"]),
            )
            for foreign_key in raw_foreign_keys
            if not self._registry.is_excluded(
                alias,
                foreign_key["referred_table"],
                foreign_key.get("referred_schema") or schema,
            )
        ]
        return TableSchema(
            name=name,
            kind=kind,
            columns=columns,
            primary_key=primary_key,
            foreign_keys=foreign_keys,
        )

    @staticmethod
    def _render_default(default: object) -> Optional[str]:
        return None if default is None else str(default)
