"""Unit tests for ReminderService against a fake ExpenseService repository.

No DynamoDB and no Sent.dm involved: the service only knows the ``Repository``
protocol (via ``ExpenseService``) and a plain ``send_reminder`` callable.
"""

from datetime import date
from typing import Any

import pytest

from src.expense.models import ExpenseIn
from src.expense.services import ExpenseService
from src.reminder.services import ReminderService


class FakeRepository:
    """Dict-backed implementation of the Repository protocol."""

    def __init__(self):
        self.items: dict[str, dict[str, Any]] = {}

    def save(self, item):
        self.items[item["id"]] = item
        return item

    def get(self, key):
        return self.items.get(key)

    def list(self):
        return list(self.items.values())

    def update(self, key, item):
        stored = {**item, "id": key}
        self.items[key] = stored
        return stored

    def delete(self, key):
        return self.items.pop(key, None) is not None


class FakeSender:
    """Records calls instead of hitting Sent.dm."""

    def __init__(self):
        self.calls: list[tuple[str, str]] = []

    def __call__(self, to: str, message: str) -> str:
        self.calls.append((to, message))
        return "fake-message-id"


@pytest.fixture(autouse=True)
def whatsapp_to(monkeypatch):
    monkeypatch.setenv("REMINDER_WHATSAPP_TO", "+15550001111")


@pytest.fixture
def sender():
    return FakeSender()


@pytest.fixture
def expense_service():
    return ExpenseService(FakeRepository(), FakeRepository())


@pytest.fixture
def service(expense_service, sender):
    return ReminderService(expense_service, send_reminder=sender)


def _create(expense_service: ExpenseService, **overrides) -> dict:
    data = {
        "description": "Electricity bill",
        "deadline": "2026-07-15",
        "value": 120.5,
        "recurrent": False,
        **overrides,
    }
    return expense_service.create(ExpenseIn(**data))


def test_no_expenses_due_tomorrow_sends_nothing(service, sender):
    result = service.run(today=date(2026, 7, 14))
    assert result.sent is False
    assert result.expense_ids == []
    assert sender.calls == []


def test_unpaid_expense_due_tomorrow_sends_reminder(service, expense_service, sender):
    created = _create(expense_service, deadline="2026-07-15")

    result = service.run(today=date(2026, 7, 14))

    assert result.sent is True
    assert result.expense_ids == [created["id"]]
    assert len(sender.calls) == 1
    to, message = sender.calls[0]
    assert to == "+15550001111"
    assert "Electricity bill" in message
    assert "120.50" in message


def test_paid_expense_due_tomorrow_is_excluded(service, expense_service, sender):
    _create(expense_service, deadline="2026-07-15", paid=True)

    result = service.run(today=date(2026, 7, 14))

    assert result.sent is False
    assert sender.calls == []


def test_expense_due_other_days_is_excluded(service, expense_service, sender):
    _create(expense_service, deadline="2026-07-20")

    result = service.run(today=date(2026, 7, 14))

    assert result.sent is False
    assert sender.calls == []


def test_expense_due_today_is_not_reminded(service, expense_service, sender):
    """The reminder fires the day *before* the deadline, not the day of."""
    _create(expense_service, deadline="2026-07-14")

    result = service.run(today=date(2026, 7, 14))

    assert result.sent is False
    assert sender.calls == []


def test_multiple_expenses_due_same_day_are_bundled_into_one_message(
    service, expense_service, sender
):
    first = _create(expense_service, description="Electricity", deadline="2026-07-15")
    second = _create(expense_service, description="Water", deadline="2026-07-15")

    result = service.run(today=date(2026, 7, 14))

    assert result.sent is True
    assert set(result.expense_ids) == {first["id"], second["id"]}
    assert len(sender.calls) == 1
    _, message = sender.calls[0]
    assert "Electricity" in message
    assert "Water" in message


def test_message_includes_observations_when_present(service, expense_service, sender):
    _create(
        expense_service,
        deadline="2026-07-15",
        observations="Pay via bank transfer, ref #123",
    )

    service.run(today=date(2026, 7, 14))

    _, message = sender.calls[0]
    assert "Pay via bank transfer, ref #123" in message


def test_message_omits_observations_when_absent(service, expense_service, sender):
    _create(expense_service, deadline="2026-07-15")

    service.run(today=date(2026, 7, 14))

    _, message = sender.calls[0]
    assert "(" not in message


def test_recurring_expense_projected_onto_tomorrow_is_included(
    service, expense_service, sender
):
    """A recurring expense's *next* occurrence, not its original deadline."""
    created = _create(
        expense_service, deadline="2026-01-15", recurrent=True
    )

    result = service.run(today=date(2026, 7, 14))

    assert result.sent is True
    assert result.expense_ids == [created["id"]]


def test_run_without_today_arg_uses_real_current_date(service, sender):
    """No expenses seeded, so this only exercises the ``today is None`` branch."""
    result = service.run()

    assert result.sent is False
    assert sender.calls == []
