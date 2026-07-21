"""Unit tests for ExpenseService against an in-memory fake Repository.

No DynamoDB (real or mocked) involved: the service only knows the
``Repository`` protocol, so a plain dict-backed fake is enough.
"""

from typing import Any

import pytest
from pydantic import ValidationError

from src.expense.exceptions import (
    ExpenseNotFoundError,
    InvalidMonthError,
    NonRecurringExpenseMonthError,
)
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
def service_with_status():
    """A service with both repositories, needed for month-scoped operations."""
    return ExpenseService(FakeRepository(), FakeRepository())


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


# --- Month-scoped listing -------------------------------------------------


def test_list_with_month_none_is_unfiltered(service, expense_in):
    created = service.create(expense_in)
    assert service.list(None) == [created]


def test_list_with_month_includes_non_recurring_in_its_own_month(
    service_with_status,
):
    expense_in = ExpenseIn(
        description="Gym", deadline="2026-07-15", value=45.0, recurrent=False
    )
    service_with_status.create(expense_in)
    assert len(service_with_status.list("2026-07")) == 1


def test_list_with_month_excludes_non_recurring_in_other_months(
    service_with_status,
):
    expense_in = ExpenseIn(
        description="Gym", deadline="2026-07-15", value=45.0, recurrent=False
    )
    service_with_status.create(expense_in)
    assert service_with_status.list("2026-08") == []


def test_list_with_month_excludes_recurring_before_it_existed(
    service_with_status,
):
    expense_in = ExpenseIn(
        description="Rent", deadline="2026-07-15", value=1500.0, recurrent=True
    )
    service_with_status.create(expense_in)
    assert service_with_status.list("2026-06") == []


def test_list_with_month_projects_recurring_deadline_forward(service_with_status):
    expense_in = ExpenseIn(
        description="Rent", deadline="2026-01-31", value=1500.0, recurrent=True
    )
    service_with_status.create(expense_in)
    # February has 28 days in 2026 (not a leap year); the 31st clamps to 28th.
    body = service_with_status.list("2026-02")
    assert len(body) == 1
    assert body[0]["deadline"] == "2026-02-28"


def test_list_with_invalid_month_raises(service_with_status):
    with pytest.raises(InvalidMonthError):
        service_with_status.list("not-a-month")


# --- Per-month paid/due isolation -----------------------------------------


def test_set_paid_on_home_month_updates_base_record(service_with_status):
    expense_in = ExpenseIn(
        description="Rent", deadline="2026-07-15", value=1500.0, recurrent=True
    )
    created = service_with_status.create(expense_in)

    updated = service_with_status.set_paid(created["id"], "2026-07", True)
    assert updated["paid"] is True
    assert service_with_status.list()[0]["paid"] is True


def test_marking_one_month_paid_does_not_affect_another_month(service_with_status):
    """The core requirement from issue #10: paid/due is tracked per month."""
    expense_in = ExpenseIn(
        description="Rent", deadline="2026-04-01", value=1500.0, recurrent=True
    )
    created = service_with_status.create(expense_in)

    service_with_status.set_paid(created["id"], "2026-04", True)

    april = service_with_status.list("2026-04")
    may = service_with_status.list("2026-05")
    assert april[0]["paid"] is True
    assert may[0]["paid"] is False

    service_with_status.set_paid(created["id"], "2026-05", True)
    april_again = service_with_status.list("2026-04")
    may_again = service_with_status.list("2026-05")
    june = service_with_status.list("2026-06")
    assert april_again[0]["paid"] is True
    assert may_again[0]["paid"] is True
    assert june[0]["paid"] is False


def test_set_paid_for_non_recurring_other_month_raises(service_with_status):
    expense_in = ExpenseIn(
        description="Gym", deadline="2026-07-15", value=45.0, recurrent=False
    )
    created = service_with_status.create(expense_in)

    with pytest.raises(NonRecurringExpenseMonthError):
        service_with_status.set_paid(created["id"], "2026-08", True)


def test_set_paid_missing_raises(service_with_status):
    with pytest.raises(ExpenseNotFoundError):
        service_with_status.set_paid("nope", "2026-07", True)


def test_set_paid_invalid_month_raises(service_with_status, expense_in):
    created = service_with_status.create(expense_in)
    with pytest.raises(InvalidMonthError):
        service_with_status.set_paid(created["id"], "bogus", True)


# --- Installments -----------------------------------------------------------


def test_installments_both_none_is_valid():
    expense_in = ExpenseIn(
        description="Gym", deadline="2026-07-15", value=45.0, recurrent=False
    )
    assert expense_in.installment_current is None
    assert expense_in.installment_total is None


def test_installments_only_current_set_raises():
    with pytest.raises(ValidationError):
        ExpenseIn(
            description="TV",
            deadline="2026-07-15",
            value=100.0,
            recurrent=False,
            installment_current=1,
        )


def test_installments_only_total_set_raises():
    with pytest.raises(ValidationError):
        ExpenseIn(
            description="TV",
            deadline="2026-07-15",
            value=100.0,
            recurrent=False,
            installment_total=3,
        )


def test_installments_total_less_than_one_raises():
    with pytest.raises(ValidationError):
        ExpenseIn(
            description="TV",
            deadline="2026-07-15",
            value=100.0,
            recurrent=False,
            installment_current=1,
            installment_total=0,
        )


def test_installments_current_greater_than_total_raises():
    with pytest.raises(ValidationError):
        ExpenseIn(
            description="TV",
            deadline="2026-07-15",
            value=100.0,
            recurrent=False,
            installment_current=4,
            installment_total=3,
        )


def test_installments_current_zero_raises():
    with pytest.raises(ValidationError):
        ExpenseIn(
            description="TV",
            deadline="2026-07-15",
            value=100.0,
            recurrent=False,
            installment_current=0,
            installment_total=3,
        )


def test_installment_expense_projects_across_months_then_stops(
    service_with_status,
):
    expense_in = ExpenseIn(
        description="TV",
        deadline="2026-07-15",
        value=300.0,
        recurrent=False,
        installment_current=1,
        installment_total=3,
    )
    created = service_with_status.create(expense_in)

    july = service_with_status.list("2026-07")
    assert len(july) == 1
    assert july[0]["installment_current"] == 1

    august = service_with_status.list("2026-08")
    assert len(august) == 1
    assert august[0]["installment_current"] == 2
    assert august[0]["deadline"] == "2026-08-15"

    september = service_with_status.list("2026-09")
    assert len(september) == 1
    assert september[0]["installment_current"] == 3

    october = service_with_status.list("2026-10")
    assert october == []
    assert created["installment_current"] == 1  # base record is untouched


def test_installment_expense_independent_of_recurrent_flag(service_with_status):
    """recurrent=False but installments set still projects into future months."""
    expense_in = ExpenseIn(
        description="Laptop",
        deadline="2026-07-01",
        value=1200.0,
        recurrent=False,
        installment_current=1,
        installment_total=2,
    )
    service_with_status.create(expense_in)

    assert len(service_with_status.list("2026-07")) == 1
    assert len(service_with_status.list("2026-08")) == 1
    assert service_with_status.list("2026-09") == []


def test_installment_paid_override_independent_per_month(service_with_status):
    expense_in = ExpenseIn(
        description="TV",
        deadline="2026-07-15",
        value=300.0,
        recurrent=False,
        installment_current=1,
        installment_total=3,
    )
    created = service_with_status.create(expense_in)

    service_with_status.set_paid(created["id"], "2026-08", True)

    august = service_with_status.list("2026-08")
    september = service_with_status.list("2026-09")
    assert august[0]["paid"] is True
    assert september[0]["paid"] is False


def test_set_paid_future_installment_month_for_non_recurring_succeeds(
    service_with_status,
):
    expense_in = ExpenseIn(
        description="TV",
        deadline="2026-07-15",
        value=300.0,
        recurrent=False,
        installment_current=1,
        installment_total=3,
    )
    created = service_with_status.create(expense_in)

    updated = service_with_status.set_paid(created["id"], "2026-08", True)
    assert updated["paid"] is True
