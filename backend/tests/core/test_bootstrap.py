"""Tests for the local table bootstrap and seeding (moto-backed)."""

from src.core.bootstrap import create_table, seed_table
from src.core.database import get_resource
from src.shared.repository import DynamoDBRepository


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


def test_seed_table_populates_dev_environment(dynamodb_table, monkeypatch, capsys):
    monkeypatch.setenv("ENVIRONMENT", "dev")
    create_table("bootstrap-expenses")
    seed_table("bootstrap-expenses")
    items = DynamoDBRepository("bootstrap-expenses").list()
    assert len(items) == 5
    assert all(item["id"].startswith("seed-") for item in items)
    assert "Seeded 5 sample expenses" in capsys.readouterr().out


def test_seed_table_is_idempotent(dynamodb_table, monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "dev")
    create_table("bootstrap-expenses")
    seed_table("bootstrap-expenses")
    seed_table("bootstrap-expenses")
    assert len(DynamoDBRepository("bootstrap-expenses").list()) == 5


def test_seed_table_skips_non_dev_environments(dynamodb_table, capsys):
    # conftest sets ENVIRONMENT=test, which is not a seedable environment.
    create_table("bootstrap-expenses")
    seed_table("bootstrap-expenses")
    assert DynamoDBRepository("bootstrap-expenses").list() == []
    assert "Skipping seed data" in capsys.readouterr().out
