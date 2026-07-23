"""Business logic for the reminder domain.

Reuses ``ExpenseService`` (and therefore ``expense/month.py``'s deadline
projection for recurring/installment expenses) to find expenses due tomorrow
that are still unpaid — no persistence of its own.
"""

from datetime import date, timedelta

from src.auth.services import list_admin_phone_numbers
from src.core.config import cognito_user_pool_id
from src.expense.repositories import expense_repository, expense_status_repository
from src.expense.services import ExpenseService
from src.reminder.models import ReminderResult
from src.reminder.sentdm_client import send_reminder


class ReminderService:
    def __init__(
        self,
        expense_service: ExpenseService,
        list_recipients=None,
        send_reminder=send_reminder,
    ):
        self.expense_service = expense_service
        self.list_recipients = list_recipients or (
            lambda: list_admin_phone_numbers(cognito_user_pool_id())
        )
        self.send_reminder = send_reminder

    def run(self, today: date | None = None) -> ReminderResult:
        """Send every admin with a phone number one WhatsApp message listing
        every unpaid expense due tomorrow.

        Sends nothing if none are due (and never calls Cognito in that case).
        Multiple expenses due the same day are bundled into a single message
        rather than one message each; the same message goes to every admin.
        """
        tomorrow = (today or date.today()) + timedelta(days=1)
        due_date = tomorrow.isoformat()

        expenses = self.expense_service.list(month=due_date[:7])
        due = [e for e in expenses if e["deadline"] == due_date and not e["paid"]]

        if not due:
            return ReminderResult(sent=False, expense_ids=[])

        message = _format_message(due)
        recipients = self.list_recipients()
        for phone_number in recipients:
            self.send_reminder(phone_number, message)

        return ReminderResult(sent=bool(recipients), expense_ids=[e["id"] for e in due])


def _format_message(expenses: list[dict]) -> str:
    """One line per expense: description, value, and observations if present."""
    lines = []
    for expense in expenses:
        line = f"{expense['description']} — {expense['value']:.2f}"
        observations = expense.get("observations")
        if observations:
            line += f" ({observations})"
        lines.append(line)
    return "\n".join(lines)


def get_reminder_service() -> ReminderService:
    """FastAPI dependency for the reminder service.

    Overridable in tests via ``app.dependency_overrides``.
    """
    return ReminderService(
        ExpenseService(expense_repository(), expense_status_repository())
    )
