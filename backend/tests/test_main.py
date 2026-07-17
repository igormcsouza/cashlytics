"""Tests for the app-level routes and exception handlers in ``src.main``."""

from botocore.exceptions import ClientError
from fastapi.testclient import TestClient

from src.expense.services import get_service


def test_health_route(client):
    res = client.get("/")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"


def test_health_route_does_not_require_auth():
    """Unlike /expenses, the health route has no require_admin dependency.

    This only proves the FastAPI app itself doesn't gate "/" — it says
    nothing about API Gateway, which is a separate enforcement point. That
    layer is exempted via HttpNoneAuthorizer on the "/" route in
    infra/stacks/backend_stack.py; there's no test crossing both layers, so
    keep them in sync by hand if either one changes.
    """
    from src.main import app

    res = TestClient(app).get("/")
    assert res.status_code == 200


class _BrokenService:
    """Service stub whose storage always fails."""

    def list(self, month=None):
        raise ClientError(
            {"Error": {"Code": "InternalServerError", "Message": "boom"}}, "Scan"
        )


def test_dynamodb_errors_return_503(client):
    from src.main import app

    app.dependency_overrides[get_service] = _BrokenService
    try:
        res = client.get("/expenses")
    finally:
        app.dependency_overrides.clear()
    assert res.status_code == 503
    assert res.json() == {"detail": "Storage temporarily unavailable"}
