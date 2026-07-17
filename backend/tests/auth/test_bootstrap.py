"""Tests for the local Cognito bootstrap (moto-backed cognito-idp)."""

import boto3
import pytest
from moto import mock_aws

from src.auth.bootstrap import ADMIN_EMAILS, DEV_PASSWORD, bootstrap, main


@pytest.fixture(autouse=True)
def cognito_local(monkeypatch):
    monkeypatch.delenv("COGNITO_ENDPOINT_URL", raising=False)
    with mock_aws():
        yield


def _client():
    return boto3.client("cognito-idp", region_name="sa-east-1")


def test_bootstrap_creates_pool_client_group_and_admins():
    pool_id, client_id = bootstrap()

    client = _client()
    pool = client.describe_user_pool(UserPoolId=pool_id)["UserPool"]
    assert pool["Name"] == "cashlytics-local"

    groups = client.list_groups(UserPoolId=pool_id)["Groups"]
    assert any(g["GroupName"] == "admin" for g in groups)

    for email in ADMIN_EMAILS:
        user = client.admin_get_user(UserPoolId=pool_id, Username=email)
        assert user["UserStatus"] == "CONFIRMED"
        membership = client.admin_list_groups_for_user(
            UserPoolId=pool_id, Username=email
        )["Groups"]
        assert any(g["GroupName"] == "admin" for g in membership)

    # The dev password must satisfy the pool's (relaxed) policy.
    auth = client.initiate_auth(
        ClientId=client_id,
        AuthFlow="USER_PASSWORD_AUTH",
        AuthParameters={"USERNAME": ADMIN_EMAILS[0], "PASSWORD": DEV_PASSWORD},
    )
    assert auth["AuthenticationResult"]["IdToken"]


def test_bootstrap_is_idempotent():
    first_pool, first_client = bootstrap()
    second_pool, second_client = bootstrap()
    assert first_pool == second_pool
    assert first_client == second_client


def test_main_writes_client_id_to_output_file(monkeypatch, tmp_path):
    output_file = tmp_path / ".cognito.env"
    monkeypatch.setattr("src.auth.bootstrap.OUTPUT_FILE", str(output_file))

    main()

    content = output_file.read_text()
    assert "NEXT_PUBLIC_COGNITO_CLIENT_ID=" in content
    assert "NEXT_PUBLIC_COGNITO_REGION=sa-east-1" in content
