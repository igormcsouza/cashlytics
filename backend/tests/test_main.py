"""Tests for the app-level routes and exception handlers in ``src.main``."""

from botocore.exceptions import ClientError

from src.expense.services import get_service


def test_health_route(client):
    res = client.get("/")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"


class _BrokenService:
    """Service stub whose storage always fails."""

    def list(self):
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
