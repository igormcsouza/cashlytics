"""Domain exceptions for the expense domain.

Raised by the service layer; translated to HTTP errors by the controllers.
"""


class ExpenseNotFoundError(Exception):
    """No expense exists with the given id."""

    def __init__(self, expense_id: str):
        self.expense_id = expense_id
        super().__init__(f"Expense '{expense_id}' not found")


class InvalidMonthError(Exception):
    """A ``month`` query/path value is not a well-formed ``YYYY-MM`` string."""

    def __init__(self, month: str):
        self.month = month
        super().__init__(f"Invalid month '{month}'; expected 'YYYY-MM'")


class NonRecurringExpenseMonthError(Exception):
    """A non-recurring expense's paid status was set for a month other than
    its own deadline's month.

    Only recurring expenses have instances in months other than their own.
    """

    def __init__(self, expense_id: str):
        self.expense_id = expense_id
        super().__init__(
            f"Expense '{expense_id}' is not recurring; its paid status can "
            "only be set for its own deadline's month"
        )
