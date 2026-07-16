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
