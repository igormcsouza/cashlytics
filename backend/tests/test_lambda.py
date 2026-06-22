"""Tests for the Lambda handler — invoked with API Gateway HTTP API events.

Uses moto-backed DynamoDB (via the ``dynamodb_table`` fixture), no real AWS.
"""

import json


def _event(method: str, path: str, body: dict | None = None) -> dict:
    """Build a minimal API Gateway HTTP API (v2) event for Mangum."""
    raw_body = json.dumps(body) if body is not None else None
    return {
        "version": "2.0",
        "routeKey": "$default",
        "rawPath": path,
        "rawQueryString": "",
        "headers": {"content-type": "application/json"},
        "requestContext": {
            "http": {
                "method": method,
                "path": path,
                "protocol": "HTTP/1.1",
                "sourceIp": "127.0.0.1",
            }
        },
        "body": raw_body,
        "isBase64Encoded": False,
    }


def test_handler_lists_expenses(dynamodb_table):
    from lambda_function import handler

    response = handler(_event("GET", "/expenses"), None)
    assert response["statusCode"] == 200
    assert json.loads(response["body"]) == []


def test_handler_creates_and_reads(dynamodb_table):
    from lambda_function import handler

    expense = {
        "description": "Internet",
        "deadline": "2026-09-01",
        "value": 59.99,
        "recurrent": True,
    }
    create = handler(_event("POST", "/expenses", expense), None)
    assert create["statusCode"] == 201
    created = json.loads(create["body"])
    assert created["description"] == "Internet"
    assert created["id"]

    listing = handler(_event("GET", "/expenses"), None)
    assert listing["statusCode"] == 200
    body = json.loads(listing["body"])
    assert len(body) == 1
    assert body[0]["id"] == created["id"]
