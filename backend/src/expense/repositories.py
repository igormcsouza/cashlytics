"""Persistence wiring for the expense domain."""

from src.core.config import table_name
from src.shared.repository import DynamoDBRepository, Repository

EXPENSES_TABLE_BASE = "expenses"
EXPENSE_STATUS_TABLE_BASE = "expense-status"


def expense_repository() -> Repository:
    """Repository bound to the environment's expenses table."""
    return DynamoDBRepository(table_name(EXPENSES_TABLE_BASE))


def expense_status_repository() -> Repository:
    """Repository bound to the environment's per-month status table.

    Stores :class:`~src.expense.models.ExpenseMonthStatus` rows, one per
    (expense, month) other than a recurring expense's own home month.
    """
    return DynamoDBRepository(table_name(EXPENSE_STATUS_TABLE_BASE))
