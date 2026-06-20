"""A generic, reusable DynamoDB repository built on boto3.

This module is intentionally free of business logic: it stores and retrieves
items by key and does no transformation beyond what DynamoDB storage requires
(floats <-> ``Decimal``). It is configured entirely from environment variables
so the same code runs against DynamoDB Local in dev and real DynamoDB in AWS.

Environment variables:
    AWS_REGION             AWS region (default: us-east-1)
    DYNAMODB_ENDPOINT_URL  Endpoint override for DynamoDB Local (unset in AWS)
"""

import json
import os
from decimal import Decimal
from functools import lru_cache
from typing import Any

import boto3

AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")
DYNAMODB_ENDPOINT_URL = os.environ.get("DYNAMODB_ENDPOINT_URL")


@lru_cache(maxsize=1)
def get_resource():
    """DynamoDB resource, initialized once at module scope (cold-start friendly)."""
    return boto3.resource(
        "dynamodb",
        region_name=AWS_REGION,
        endpoint_url=DYNAMODB_ENDPOINT_URL,
    )


def _to_dynamo(item: dict[str, Any]) -> dict[str, Any]:
    """Convert floats to Decimal as required by the DynamoDB SDK."""
    return json.loads(json.dumps(item), parse_float=Decimal)


def _from_dynamo(item: dict[str, Any]) -> dict[str, Any]:
    """Convert DynamoDB Decimals back to native int/float."""
    out: dict[str, Any] = {}
    for key, value in item.items():
        if isinstance(value, Decimal):
            out[key] = int(value) if value % 1 == 0 else float(value)
        else:
            out[key] = value
    return out


class DynamoDBRepository:
    """Generic key/value-ish access over a single DynamoDB table."""

    def __init__(self, table_name: str, key_name: str = "id"):
        self.table_name = table_name
        self.key_name = key_name
        self.table = get_resource().Table(table_name)

    def save(self, item: dict[str, Any]) -> dict[str, Any]:
        """Persist a complete item (create or full overwrite)."""
        self.table.put_item(Item=_to_dynamo(item))
        return item

    def get(self, key: str) -> dict[str, Any] | None:
        """Fetch a single item by its partition key."""
        response = self.table.get_item(Key={self.key_name: key})
        item = response.get("Item")
        return _from_dynamo(item) if item is not None else None

    def list(self) -> list[dict[str, Any]]:
        """Return all items in the table."""
        items: list[dict[str, Any]] = []
        response = self.table.scan()
        items.extend(response.get("Items", []))
        while "LastEvaluatedKey" in response:
            response = self.table.scan(
                ExclusiveStartKey=response["LastEvaluatedKey"]
            )
            items.extend(response.get("Items", []))
        return [_from_dynamo(item) for item in items]

    def update(self, key: str, item: dict[str, Any]) -> dict[str, Any]:
        """Overwrite the item at ``key`` with ``item`` (full replace)."""
        stored = {**item, self.key_name: key}
        self.table.put_item(Item=_to_dynamo(stored))
        return stored

    def delete(self, key: str) -> bool:
        """Delete an item by key. Returns True if an item was deleted."""
        response = self.table.delete_item(
            Key={self.key_name: key}, ReturnValues="ALL_OLD"
        )
        return response.get("Attributes") is not None
