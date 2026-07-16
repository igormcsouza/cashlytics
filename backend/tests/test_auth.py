"""Tests for the role-based auth dependency (backend/auth.py)."""

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from starlette.requests import Request

from auth import groups_from_claims, require_admin
from conftest import WithGatewayClaims


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
    def test_no_claims_rejected(self):
        with pytest.raises(HTTPException) as exc:
            require_admin(make_request())
        assert exc.value.status_code == 401

    def test_non_admin_rejected(self):
        with pytest.raises(HTTPException) as exc:
            require_admin(make_request({"cognito:groups": "[viewer]"}))
        assert exc.value.status_code == 403

    def test_admin_allowed(self):
        claims = {"email": "a@b.c", "cognito:groups": "[admin]"}
        assert require_admin(make_request(claims)) == claims


def test_api_rejects_unauthenticated_requests():
    """Without authorizer claims every expense route is 401."""
    from app import app

    client = TestClient(app)
    assert client.get("/expenses").status_code == 401
    assert client.post("/expenses", json={}).status_code == 401
    assert client.put("/expenses/x", json={}).status_code == 401
    assert client.delete("/expenses/x").status_code == 401
    # Health has no role requirement (the authorizer still guards it in AWS).
    assert client.get("/").status_code == 200


def test_api_rejects_non_admin_requests():
    """A valid token without the admin group is 403."""
    from app import app

    client = TestClient(
        WithGatewayClaims(app, {"email": "v@x.y", "cognito:groups": "[viewer]"})
    )
    assert client.get("/expenses").status_code == 403
