"""Domain exceptions for the expense domain.

Raised by the service layer; translated to HTTP errors by the controllers.
"""


class ExpenseNotFoundError(Exception):
    """No expense exists with the given id."""

    def __init__(self, expense_id: str):
        self.expense_id = expense_id
        super().__init__(f"Expense '{expense_id}' not found")
