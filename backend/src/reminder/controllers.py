"""HTTP routes for the reminder domain.

Only a manual-trigger endpoint: the daily run is normally fired by the
scheduled Lambda (see ``reminder_lambda_function.py`` / the ``ReminderFunction``
+ EventBridge rule in ``infra/stacks/backend_stack.py``), not this router.
This exists for manual QA/ops — resending on demand without waiting for the
schedule.
"""

from fastapi import APIRouter, Depends, HTTPException

from src.auth.services import require_admin
from src.reminder.exceptions import ReminderSendError
from src.reminder.models import ReminderResult
from src.reminder.services import ReminderService, get_reminder_service

router = APIRouter(
    prefix="/reminders", tags=["reminders"], dependencies=[Depends(require_admin)]
)


@router.post("/run")
def run_reminder(
    service: ReminderService = Depends(get_reminder_service),
) -> ReminderResult:
    try:
        return service.run()
    except ReminderSendError as exc:
        raise HTTPException(status_code=502, detail=str(exc))
