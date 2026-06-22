"""Pydantic models used by the database layer.

Only data shape lives here — no business logic, no persistence code.
"""

import uuid

from pydantic import BaseModel, Field


class Expense(BaseModel):
    """An expense as stored in DynamoDB.

    ``id`` is the partition key, a generated UUID string (replacing the old
    MongoDB ``_id``).
    """

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    description: str
    deadline: str
    value: float
    recurrent: bool
