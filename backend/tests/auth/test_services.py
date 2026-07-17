"""Unit tests for the role-based auth dependency (src/auth/services.py)."""

import pytest
from fastapi import HTTPException
from starlette.requests import Request

from src.auth.services import groups_from_claims, require_admin


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
