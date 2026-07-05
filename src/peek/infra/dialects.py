"""Maps SQLAlchemy dialect names to ``sqlglot`` dialect names.

SQLAlchemy and ``sqlglot`` name the same backends differently (for example
SQLAlchemy's ``postgresql`` versus ``sqlglot``'s ``postgres``). The safety
guard parses in a ``sqlglot`` dialect, so an alias's SQLAlchemy dialect name is
translated here before it reaches the guard. An unknown name maps to ``None``,
which tells the guard to parse with its generic dialect.
"""

from typing import Dict, Optional

_SQLALCHEMY_TO_SQLGLOT: Dict[str, str] = {
    "postgresql": "postgres",
    "mysql": "mysql",
    "mariadb": "mysql",
    "mssql": "tsql",
    "oracle": "oracle",
    "sqlite": "sqlite",
}


def to_sqlglot_dialect(sqlalchemy_name: str) -> Optional[str]:
    """Translate a SQLAlchemy dialect name to a ``sqlglot`` dialect name.

    Args:
        sqlalchemy_name: The SQLAlchemy ``Dialect.name`` (for example
            ``"postgresql"``).

    Returns:
        The matching ``sqlglot`` dialect name, or ``None`` when the backend has
        no known mapping (the guard then parses with its generic dialect).
    """
    return _SQLALCHEMY_TO_SQLGLOT.get(sqlalchemy_name.lower())
