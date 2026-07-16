"""Persistence wiring for the expense domain."""

from src.core.config import table_name
from src.shared.repository import DynamoDBRepository, Repository

EXPENSES_TABLE_BASE = "expenses"


def expense_repository() -> Repository:
    """Repository bound to the environment's expenses table."""
    return DynamoDBRepository(table_name(EXPENSES_TABLE_BASE))
