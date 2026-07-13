"""Tests for the schema introspection service."""

from pathlib import Path

import pytest
from sqlalchemy import create_engine, text

from peek.config import AppConfig
from peek.errors import RegistryError, SchemaError
from peek.services.connection_registry import ConnectionRegistry
from peek.services.schema_service import SchemaService


def _make_database(tmp_path: Path) -> str:
    db_path = tmp_path / "app.db"
    # as_posix(): a Windows path's backslashes would be read as escape
    # sequences inside the TOML basic string this url is written into.
    url = f"sqlite:///{db_path.as_posix()}"
    engine = create_engine(url)
    with engine.begin() as connection:
        connection.execute(
            text(
                "CREATE TABLE users ("
                "id INTEGER PRIMARY KEY, name TEXT NOT NULL)"
            )
        )
        connection.execute(
            text(
                "CREATE TABLE orders ("
                "id INTEGER PRIMARY KEY, "
                "user_id INTEGER NOT NULL REFERENCES users(id), "
                "total NUMERIC)"
            )
        )
        connection.execute(
            text("CREATE VIEW active_users AS SELECT id, name FROM users")
        )
    engine.dispose()
    return url


def _service(tmp_path: Path, url: str) -> SchemaService:
    config_path = tmp_path / "databases.toml"
    config_path.write_text(f'[databases.main]\nurl = "{url}"\n')
    config = AppConfig(config_file=config_path)
    return SchemaService(ConnectionRegistry.from_config(config))


@pytest.fixture
def service(tmp_path: Path) -> SchemaService:
    return _service(tmp_path, _make_database(tmp_path))


def test_list_tables_includes_tables_and_views(
    service: SchemaService,
) -> None:
    """list_tables reports every table and view tagged by kind."""
    listing = service.list_tables("main")

    kinds = {info.name: info.kind for info in listing.tables}
    assert kinds == {
        "users": "table",
        "orders": "table",
        "active_users": "view",
    }
    assert listing.hidden_count == 0


def test_get_schema_returns_columns_pk_and_fk(
    service: SchemaService,
) -> None:
    """get_schema returns structured columns, primary key, and foreign keys."""
    result = service.get_schema("main", tables=["orders"])

    assert len(result.tables) == 1
    orders = result.tables[0]
    assert orders.kind == "table"
    assert orders.primary_key == ["id"]

    columns = {column.name: column for column in orders.columns}
    assert set(columns) == {"id", "user_id", "total"}
    assert columns["id"].primary_key is True
    assert "INT" in columns["id"].type.upper()
    assert columns["user_id"].nullable is False

    assert len(orders.foreign_keys) == 1
    foreign_key = orders.foreign_keys[0]
    assert foreign_key.columns == ["user_id"]
    assert foreign_key.references_table == "users"
    assert foreign_key.references_columns == ["id"]


def test_get_schema_paginates_with_limit_and_offset(
    service: SchemaService,
) -> None:
    """limit/offset page through every table, flagging truncation."""
    first = service.get_schema("main", limit=1, offset=0)
    assert len(first.tables) == 1
    assert first.total_tables == 3
    assert first.truncated is True

    rest = service.get_schema("main", limit=10, offset=1)
    assert len(rest.tables) == 2
    assert rest.total_tables == 3
    assert rest.truncated is False


def test_get_schema_unknown_table_raises_schema_error(
    service: SchemaService,
) -> None:
    """A requested table that does not exist raises SchemaError."""
    with pytest.raises(SchemaError) as excinfo:
        service.get_schema("main", tables=["ghost"])

    message = str(excinfo.value)
    assert "ghost" in message
    assert "main" in message


def test_negative_pagination_bounds_raise_schema_error(
    service: SchemaService,
) -> None:
    """Negative limit or offset is rejected."""
    with pytest.raises(SchemaError):
        service.get_schema("main", offset=-1)


def test_get_schema_unknown_alias_raises_registry_error(
    service: SchemaService,
) -> None:
    """An unknown alias surfaces as RegistryError."""
    with pytest.raises(RegistryError):
        service.get_schema("does-not-exist")


def test_excluded_table_is_invisible_everywhere(tmp_path: Path) -> None:
    """A denied table vanishes from listing, get_schema, and foreign keys."""
    url = _make_database(tmp_path)
    config_path = tmp_path / "databases.toml"
    config_path.write_text(
        f'[databases.main]\nurl = "{url}"\nexclude_tables = ["users"]\n'
    )
    config = AppConfig(config_file=config_path)
    service = SchemaService(ConnectionRegistry.from_config(config))

    listing = service.list_tables("main")
    names = {info.name for info in listing.tables}
    assert "users" not in names
    assert listing.hidden_count == 1

    with pytest.raises(SchemaError):
        service.get_schema("main", tables=["users"])

    paged = service.get_schema("main")
    assert all(table.name != "users" for table in paged.tables)
    assert paged.hidden_count == 1

    orders = service.get_schema("main", tables=["orders"]).tables[0]
    assert orders.foreign_keys == []


def test_schema_output_and_errors_carry_no_connection_string(
    tmp_path: Path,
) -> None:
    """No return value or error ever echoes the connection string."""
    url = _make_database(tmp_path)
    service = _service(tmp_path, url)

    result = service.get_schema("main")
    assert url not in repr(result)

    with pytest.raises(SchemaError) as excinfo:
        service.get_schema("main", tables=["ghost"])
    assert url not in str(excinfo.value)
