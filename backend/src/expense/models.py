"""Pydantic models for the expense domain.

Only data shape lives here — no business logic, no persistence code. An invalid
request body is rejected by FastAPI with HTTP 422 and a structured error
payload.
"""

import uuid
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


def _check_installments(current: int | None, total: int | None) -> None:
    """Validate the (current, total) installment pair.

    Both must be set or both omitted; when set, ``total`` must be at least 1
    and ``current`` must fall within ``[1, total]``.
    """
    if (current is None) != (total is None):
        raise ValueError(
            "installment_current and installment_total must both be set or both omitted"
        )
    if total is not None:
        if total < 1:
            raise ValueError("installment_total must be >= 1")
        if not (1 <= current <= total):
            raise ValueError(
                "installment_current must be between 1 and installment_total"
            )


EXPENSE_CATEGORIES = ("Housing", "Leisure", "Food", "Transport", "Health", "Other")
ExpenseCategory = Literal[EXPENSE_CATEGORIES]


class ExpenseIn(BaseModel):
    """Request body for creating/updating an expense."""

    model_config = ConfigDict(extra="ignore")

    description: str
    deadline: str
    value: float
    recurrent: bool
    paid: bool = False
    category: ExpenseCategory | None = None
    installment_current: int | None = None
    installment_total: int | None = None

    @model_validator(mode="after")
    def _validate_installments(self):
        _check_installments(self.installment_current, self.installment_total)
        return self


class Expense(BaseModel):
    """An expense as stored in DynamoDB.

    ``id`` is the partition key, a generated UUID string.
    """

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    description: str
    deadline: str
    value: float
    recurrent: bool
    paid: bool = False
    category: ExpenseCategory | None = None
    installment_current: int | None = None
    installment_total: int | None = None

    @model_validator(mode="after")
    def _validate_installments(self):
        _check_installments(self.installment_current, self.installment_total)
        return self


class PaidStatusIn(BaseModel):
    """Request body for marking a specific month's instance paid/due."""

    model_config = ConfigDict(extra="ignore")

    paid: bool


class ExpenseMonthStatus(BaseModel):
    """Per-month paid/due override for a recurring expense instance.

    A recurring expense (e.g. rent) has a single ``Expense`` record, but its
    paid/due status must be tracked independently for every month it recurs
    into — marking April's instance paid must not mark May's paid too. Rather
    than extend the repository with composite (partition + sort) key
    support, this stores one row per (expense, month) in its own table, keyed
    by a composite ``id`` of ``"{expense_id}#{month}"`` so it fits the
    existing generic single-key repository unchanged.

    The expense's *home* month (the month its own ``deadline`` falls in) is
    tracked on the ``Expense`` record itself via its ``paid`` field, as
    before; rows here only exist for *other* months of a recurring expense.
    """

    id: str
    expense_id: str
    month: str
    paid: bool = False
