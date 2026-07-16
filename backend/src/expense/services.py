"""Business logic for the expense domain.

Depends only on the ``Repository`` protocol, so it can run against DynamoDB in
production or an in-memory fake in tests.
"""

from src.expense.exceptions import ExpenseNotFoundError
from src.expense.models import Expense, ExpenseIn
from src.shared.repository import Repository


class ExpenseService:
    """CRUD operations over expenses, storage-agnostic."""

    def __init__(self, repository: Repository):
        self.repository = repository

    def list(self) -> list[dict]:
        return self.repository.list()

    def create(self, expense: ExpenseIn) -> dict:
        created = Expense(**expense.model_dump())
        return self.repository.save(created.model_dump())

    def update(self, expense_id: str, expense: ExpenseIn) -> dict:
        if self.repository.get(expense_id) is None:
            raise ExpenseNotFoundError(expense_id)
        updated = Expense(id=expense_id, **expense.model_dump())
        return self.repository.save(updated.model_dump())

    def delete(self, expense_id: str) -> None:
        if not self.repository.delete(expense_id):
            raise ExpenseNotFoundError(expense_id)
