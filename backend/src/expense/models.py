"""Pydantic models for the expense domain.

Only data shape lives here — no business logic, no persistence code. An invalid
request body is rejected by FastAPI with HTTP 422 and a structured error
payload.
"""

import uuid

from pydantic import BaseModel, ConfigDict, Field


class ExpenseIn(BaseModel):
    """Request body for creating/updating an expense."""

    model_config = ConfigDict(extra="ignore")

    description: str
    deadline: str
    value: float
    recurrent: bool
    paid: bool = False


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
