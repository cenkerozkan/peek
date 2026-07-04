"""Tests for :class:`peek.models.config.DatabaseEntry`."""

from pydantic import SecretStr

from src.peek.models.config import DatabaseEntry


def test_repr_does_not_leak_password() -> None:
    """SecretStr masks the password in repr() and str()."""
    entry = DatabaseEntry(url=SecretStr("postgresql://user:hunter2@host/db"))

    assert "hunter2" not in repr(entry)
    assert "hunter2" not in str(entry)


def test_get_secret_value_returns_the_url() -> None:
    """The raw URL is only reachable via get_secret_value()."""
    url = "postgresql://user:hunter2@host/db"
    entry = DatabaseEntry(url=SecretStr(url))

    assert entry.url.get_secret_value() == url


def test_dialect_defaults_to_none() -> None:
    """Dialect is an optional override."""
    entry = DatabaseEntry(url=SecretStr("sqlite://"))

    assert entry.dialect is None
