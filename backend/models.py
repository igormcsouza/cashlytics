"""Pydantic models for the expenses API request bodies.

Replaces the hand-rolled ``validate_expense`` helper. An invalid request body
is rejected by FastAPI with HTTP 422 and a structured error payload.
"""

from pydantic import BaseModel, ConfigDict


class ExpenseIn(BaseModel):
    """Request body for creating/updating an expense."""

    model_config = ConfigDict(extra="ignore")

    description: str
    deadline: str
    value: float
    recurrent: bool
