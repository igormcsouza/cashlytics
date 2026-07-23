"""Pydantic models for the reminder domain.

No stored shape here — the reminder job owns no table of its own (it reuses
the expense domain's repositories/service), so this only holds the result of
running the job.
"""

from pydantic import BaseModel


class ReminderResult(BaseModel):
    """Outcome of a single :meth:`~src.reminder.services.ReminderService.run`."""

    sent: bool
    expense_ids: list[str] = []
