"""Tests for the local table bootstrap (moto-backed)."""

from src.core.bootstrap import create_table
from src.core.database import get_resource


def _table_names():
    return get_resource().meta.client.list_tables()["TableNames"]


def test_create_table(dynamodb_table, capsys):
    create_table("bootstrap-expenses")
    assert "bootstrap-expenses" in _table_names()
    assert "Created table 'bootstrap-expenses'." in capsys.readouterr().out


def test_create_table_is_idempotent(dynamodb_table, capsys):
    create_table("bootstrap-expenses")
    create_table("bootstrap-expenses")
    assert _table_names().count("bootstrap-expenses") == 1
    assert "already exists" in capsys.readouterr().out
