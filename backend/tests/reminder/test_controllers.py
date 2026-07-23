"""API tests for the reminder routes.

The manual-trigger route is admin-only, same as the expense routes.
``get_reminder_service`` is overridden with a fake so no real DynamoDB list or
Sent.dm call happens here — that logic is covered by test_services.py.
"""

from fastapi.testclient import TestClient

from conftest import WithGatewayClaims
from src.reminder.models import ReminderResult
from src.reminder.services import get_reminder_service


class FakeReminderService:
    def __init__(self, result: ReminderResult):
        self._result = result

    def run(self) -> ReminderResult:
        return self._result


def test_reminders_require_authentication():
    from src.main import app

    unauthenticated = TestClient(app)
    assert unauthenticated.post("/reminders/run").status_code == 401


def test_reminders_require_admin_group():
    from src.main import app

    viewer = TestClient(
        WithGatewayClaims(app, {"email": "v@x.y", "cognito:groups": "[viewer]"})
    )
    assert viewer.post("/reminders/run").status_code == 403


def test_run_reminder_returns_result(client):
    from src.main import app

    fake = FakeReminderService(ReminderResult(sent=True, expense_ids=["abc"]))
    app.dependency_overrides[get_reminder_service] = lambda: fake
    try:
        res = client.post("/reminders/run")
        assert res.status_code == 200
        assert res.json() == {"sent": True, "expense_ids": ["abc"]}
    finally:
        app.dependency_overrides.pop(get_reminder_service, None)
