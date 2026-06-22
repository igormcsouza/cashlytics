import os

import boto3
import pytest
from fastapi.testclient import TestClient
from moto import mock_aws

TABLE_NAME = "test-expenses"


@pytest.fixture(autouse=True)
def aws_credentials(monkeypatch):
    """Dummy credentials so boto3/moto never touch real AWS."""
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
    monkeypatch.setenv("AWS_REGION", "us-east-1")
    # app/bootstrap compose "<ENVIRONMENT>-expenses"; "test" -> "test-expenses".
    monkeypatch.setenv("ENVIRONMENT", "test")
    # Ensure no leftover endpoint override points us at DynamoDB Local.
    monkeypatch.delenv("DYNAMODB_ENDPOINT_URL", raising=False)


@pytest.fixture
def dynamodb_table(aws_credentials):
    with mock_aws():
        # Clear the cached boto3 resource so it binds to the moto mock.
        from database import repository

        repository.get_resource.cache_clear()
        resource = boto3.resource("dynamodb", region_name="us-east-1")
        resource.create_table(
            TableName=TABLE_NAME,
            KeySchema=[{"AttributeName": "id", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "id", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )
        resource.Table(TABLE_NAME).wait_until_exists()
        yield resource.Table(TABLE_NAME)
        repository.get_resource.cache_clear()


@pytest.fixture
def repository(dynamodb_table):
    from database.repository import DynamoDBRepository

    return DynamoDBRepository(TABLE_NAME)


@pytest.fixture
def client(dynamodb_table):
    from app import app

    with TestClient(app) as c:
        yield c


@pytest.fixture
def sample_expense():
    return {
        "description": "Electricity bill",
        "deadline": "2026-07-01",
        "value": 120.5,
        "recurrent": True,
    }
