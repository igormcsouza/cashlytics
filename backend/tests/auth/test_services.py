"""Unit tests for the role-based auth dependency (src/auth/services.py)."""

import boto3
import pytest
from fastapi import HTTPException
from moto import mock_aws
from starlette.requests import Request

from src.auth.services import (
    ADMIN_GROUP,
    groups_from_claims,
    list_admin_phone_numbers,
    require_admin,
)


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


def _pool_with_admin_group(client) -> str:
    pool_id = client.create_user_pool(PoolName="test")["UserPool"]["Id"]
    client.create_group(UserPoolId=pool_id, GroupName=ADMIN_GROUP)
    return pool_id


class TestListAdminPhoneNumbers:
    """Uses moto's cognitoidp mock — no real AWS."""

    def test_returns_phone_numbers_for_users_that_have_one(self):
        with mock_aws():
            client = boto3.client("cognito-idp", region_name="sa-east-1")
            pool_id = _pool_with_admin_group(client)
            client.admin_create_user(
                UserPoolId=pool_id,
                Username="a@x.com",
                UserAttributes=[
                    {"Name": "email", "Value": "a@x.com"},
                    {"Name": "phone_number", "Value": "+15550001111"},
                ],
                MessageAction="SUPPRESS",
            )
            client.admin_add_user_to_group(
                UserPoolId=pool_id, Username="a@x.com", GroupName=ADMIN_GROUP
            )

            assert list_admin_phone_numbers(pool_id) == ["+15550001111"]

    def test_skips_users_without_a_phone_number(self):
        with mock_aws():
            client = boto3.client("cognito-idp", region_name="sa-east-1")
            pool_id = _pool_with_admin_group(client)
            client.admin_create_user(
                UserPoolId=pool_id,
                Username="a@x.com",
                UserAttributes=[{"Name": "email", "Value": "a@x.com"}],
                MessageAction="SUPPRESS",
            )
            client.admin_add_user_to_group(
                UserPoolId=pool_id, Username="a@x.com", GroupName=ADMIN_GROUP
            )

            assert list_admin_phone_numbers(pool_id) == []

    def test_empty_group_returns_empty_list(self):
        with mock_aws():
            client = boto3.client("cognito-idp", region_name="sa-east-1")
            pool_id = _pool_with_admin_group(client)

            assert list_admin_phone_numbers(pool_id) == []

    def test_paginates_through_multiple_pages(self, monkeypatch):
        """A fake client, not moto: deterministically forces a second page,
        which real-world usage (two known admins) never triggers on its own."""
        import src.auth.services as services_module

        class FakeCognitoClient:
            def __init__(self):
                self.calls: list[dict] = []

            def list_users_in_group(self, **kwargs):
                self.calls.append(kwargs)
                if "NextToken" not in kwargs:
                    return {
                        "Users": [
                            {
                                "Attributes": [
                                    {"Name": "phone_number", "Value": "+15550001111"}
                                ]
                            }
                        ],
                        "NextToken": "page-2",
                    }
                return {
                    "Users": [
                        {
                            "Attributes": [
                                {"Name": "phone_number", "Value": "+15550002222"}
                            ]
                        }
                    ]
                }

        fake_client = FakeCognitoClient()
        monkeypatch.setattr(
            services_module.boto3, "client", lambda *a, **k: fake_client
        )

        numbers = list_admin_phone_numbers("pool-1")

        assert numbers == ["+15550001111", "+15550002222"]
        assert len(fake_client.calls) == 2
        assert "NextToken" not in fake_client.calls[0]
        assert fake_client.calls[1]["NextToken"] == "page-2"
