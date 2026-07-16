"""Tests for the role-based auth dependency (backend/auth.py)."""

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from starlette.requests import Request

from auth import groups_from_claims, require_admin


def make_request(claims: dict | None = None) -> Request:
    """Build a Request whose scope mimics Mangum behind the JWT authorizer."""
    scope = {"type": "http", "method": "GET", "path": "/", "headers": []}
    if claims is not None:
        scope["aws.event"] = {
            "requestContext": {"authorizer": {"jwt": {"claims": claims}}}
        }
    return Request(scope)


class TestGroupsFromClaims:
    def test_list_form(self):
        assert groups_from_claims({"cognito:groups": ["admin", "other"]}) == [
            "admin",
            "other",
        ]

    def test_authorizer_string_form(self):
        # The HTTP API JWT authorizer serialises the list as "[a b]" or "[a,b]".
        assert groups_from_claims({"cognito:groups": "[admin other]"}) == [
            "admin",
            "other",
        ]
        assert groups_from_claims({"cognito:groups": "[admin,other]"}) == [
            "admin",
            "other",
        ]

    def test_missing(self):
        assert groups_from_claims({}) == []


class TestRequireAdmin:
    def test_no_claims_rejected(self, monkeypatch):
        monkeypatch.delenv("AUTH_BYPASS", raising=False)
        with pytest.raises(HTTPException) as exc:
            require_admin(make_request())
        assert exc.value.status_code == 401

    def test_non_admin_rejected(self, monkeypatch):
        monkeypatch.delenv("AUTH_BYPASS", raising=False)
        with pytest.raises(HTTPException) as exc:
            require_admin(make_request({"cognito:groups": "[viewer]"}))
        assert exc.value.status_code == 403

    def test_admin_allowed(self, monkeypatch):
        monkeypatch.delenv("AUTH_BYPASS", raising=False)
        claims = {"email": "a@b.c", "cognito:groups": "[admin]"}
        assert require_admin(make_request(claims)) == claims

    def test_bypass_allows_without_event(self, monkeypatch):
        monkeypatch.setenv("AUTH_BYPASS", "true")
        claims = require_admin(make_request())
        assert "admin" in claims["cognito:groups"]

    def test_bypass_does_not_skip_role_check(self, monkeypatch):
        # A real (non-admin) token must be rejected even with bypass on.
        monkeypatch.setenv("AUTH_BYPASS", "true")
        with pytest.raises(HTTPException) as exc:
            require_admin(make_request({"cognito:groups": "[viewer]"}))
        assert exc.value.status_code == 403


def test_api_rejects_unauthenticated_requests(monkeypatch):
    """Without bypass or gateway claims every expense route is 401."""
    monkeypatch.delenv("AUTH_BYPASS", raising=False)
    from app import app

    client = TestClient(app)
    assert client.get("/expenses").status_code == 401
    assert client.post("/expenses", json={}).status_code == 401
    assert client.put("/expenses/x", json={}).status_code == 401
    assert client.delete("/expenses/x").status_code == 401
    # Health stays open at the app level (the gateway still protects it in AWS).
    assert client.get("/").status_code == 200
