"""Unit tests for ExpenseService against an in-memory fake Repository.

No DynamoDB (real or mocked) involved: the service only knows the
``Repository`` protocol, so a plain dict-backed fake is enough.
"""

from typing import Any

import pytest

from src.expense.exceptions import ExpenseNotFoundError
from src.expense.models import ExpenseIn
from src.expense.services import ExpenseService


class FakeRepository:
    """Dict-backed implementation of the Repository protocol."""

    def __init__(self):
        self.items: dict[str, dict[str, Any]] = {}

    def save(self, item: dict[str, Any]) -> dict[str, Any]:
        self.items[item["id"]] = item
        return item

    def get(self, key: str) -> dict[str, Any] | None:
        return self.items.get(key)

    def list(self) -> list[dict[str, Any]]:
        return list(self.items.values())

    def update(self, key: str, item: dict[str, Any]) -> dict[str, Any]:
        stored = {**item, "id": key}
        self.items[key] = stored
        return stored

    def delete(self, key: str) -> bool:
        return self.items.pop(key, None) is not None


@pytest.fixture
def service():
    return ExpenseService(FakeRepository())


@pytest.fixture
def expense_in():
    return ExpenseIn(
        description="Water bill",
        deadline="2026-07-20",
        value=45.0,
        recurrent=True,
    )


def test_create_assigns_id_and_persists(service, expense_in):
    created = service.create(expense_in)
    assert created["id"]
    assert created["description"] == "Water bill"
    assert service.list() == [created]


def test_create_defaults_paid_to_false(service, expense_in):
    assert service.create(expense_in)["paid"] is False


def test_list_empty(service):
    assert service.list() == []


def test_update_overwrites_and_keeps_id(service, expense_in):
    created = service.create(expense_in)
    updated = service.update(
        created["id"], expense_in.model_copy(update={"value": 99.9})
    )
    assert updated["id"] == created["id"]
    assert updated["value"] == 99.9


def test_update_missing_raises(service, expense_in):
    with pytest.raises(ExpenseNotFoundError) as exc:
        service.update("nope", expense_in)
    assert exc.value.expense_id == "nope"


def test_delete_removes(service, expense_in):
    created = service.create(expense_in)
    service.delete(created["id"])
    assert service.list() == []


def test_delete_missing_raises(service):
    with pytest.raises(ExpenseNotFoundError):
        service.delete("nope")
