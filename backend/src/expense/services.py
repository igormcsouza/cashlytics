"""Business logic for the expense domain.

Depends only on the ``Repository`` protocol, so it can run against DynamoDB in
production or an in-memory fake in tests.
"""

from src.expense.exceptions import (
    ExpenseNotFoundError,
    InvalidMonthError,
    NonRecurringExpenseMonthError,
)
from src.expense.models import Expense, ExpenseIn, ExpenseMonthStatus
from src.expense.month import (
    home_month,
    is_valid_month,
    month_status_id,
    months_diff,
    project_deadline,
)
from src.expense.repositories import expense_repository, expense_status_repository
from src.shared.repository import Repository


class ExpenseService:
    """CRUD operations over expenses, storage-agnostic.

    ``status_repository`` is only needed for month-scoped operations
    (``list`` with a ``month``, and ``set_paid``); it defaults to ``None`` so
    callers that never scope by month (and existing tests) don't need to
    provide one.
    """

    def __init__(self, repository: Repository, status_repository: Repository | None = None):
        self.repository = repository
        self.status_repository = status_repository

    def list(self, month: str | None = None) -> list[dict]:
        """List expenses, optionally scoped to a single ``month`` (``YYYY-MM``).

        Without ``month`` every stored expense is returned unchanged (back-compat
        with existing callers/tests). With ``month``:

        - Non-recurring, non-installment expenses are only included if their own
          deadline falls in that month.
        - Recurring expenses (and installment expenses, which recur regardless of
          the ``recurrent`` flag) are included from their own deadline's month
          onward (an expense can't have an instance before it existed). Their
          deadline is projected onto the requested month (same day-of-month,
          clamped to the month's length), and their paid status for any month
          other than their own is looked up independently so that marking one
          month's instance paid never affects another month.
        - Installment expenses stop appearing once the installment counter
          (``installment_current`` plus the month offset) exceeds
          ``installment_total``.
        """
        expenses = self.repository.list()
        if month is None:
            return expenses

        if not is_valid_month(month):
            raise InvalidMonthError(month)

        result: list[dict] = []
        for expense in expenses:
            expense_home_month = home_month(expense["deadline"])
            installment_total = expense.get("installment_total")
            installment_current = expense.get("installment_current")
            has_installments = (
                installment_total is not None and installment_current is not None
            )
            recurs = expense["recurrent"] or has_installments

            if not recurs:
                if expense_home_month == month:
                    result.append(expense)
                continue

            if month < expense_home_month:
                continue

            offset = months_diff(expense_home_month, month)
            if has_installments and installment_current + offset > installment_total:
                continue  # installments exhausted — no instance this month

            if offset == 0:
                result.append(expense)
                continue

            status_row = self.status_repository.get(
                month_status_id(expense["id"], month)
            )
            projected = {
                **expense,
                "deadline": project_deadline(expense["deadline"], month),
                "paid": status_row["paid"] if status_row else False,
            }
            if has_installments:
                projected["installment_current"] = installment_current + offset
            result.append(projected)
        return result

    def create(self, expense: ExpenseIn) -> dict:
        created = Expense(**expense.model_dump())
        return self.repository.save(created.model_dump())

    def update(self, expense_id: str, expense: ExpenseIn) -> dict:
        if self.repository.get(expense_id) is None:
            raise ExpenseNotFoundError(expense_id)
        updated = Expense(id=expense_id, **expense.model_dump())
        return self.repository.save(updated.model_dump())

    def set_paid(self, expense_id: str, month: str, paid: bool) -> dict:
        """Mark a specific month's instance of an expense paid/due.

        For the expense's own home month this updates the ``Expense`` record's
        ``paid`` field directly (same storage as before). For any other month of
        a recurring expense, the status is stored independently keyed by
        (expense_id, month) so it never leaks into another month's view.
        """
        if not is_valid_month(month):
            raise InvalidMonthError(month)

        expense = self.repository.get(expense_id)
        if expense is None:
            raise ExpenseNotFoundError(expense_id)

        expense_home_month = home_month(expense["deadline"])
        if month == expense_home_month:
            updated = {**expense, "paid": paid}
            self.repository.save(updated)
            return updated

        if not expense["recurrent"] and not (
            expense.get("installment_total") is not None
            and expense.get("installment_current") is not None
        ):
            raise NonRecurringExpenseMonthError(expense_id)

        status_id = month_status_id(expense_id, month)
        status_row = ExpenseMonthStatus(
            id=status_id, expense_id=expense_id, month=month, paid=paid
        )
        self.status_repository.save(status_row.model_dump())
        return {
            **expense,
            "deadline": project_deadline(expense["deadline"], month),
            "paid": paid,
        }

    def delete(self, expense_id: str) -> None:
        if not self.repository.delete(expense_id):
            raise ExpenseNotFoundError(expense_id)


def get_service() -> ExpenseService:
    """FastAPI dependency for the expense service.

    Overridable in tests via ``app.dependency_overrides``.
    """
    return ExpenseService(expense_repository(), expense_status_repository())
