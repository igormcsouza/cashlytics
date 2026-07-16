"""Generic repository abstractions shared by every domain.

``Repository`` is a structural interface (:class:`typing.Protocol`): services
depend on it instead of a concrete storage class, so storage backends can be
swapped (or faked in tests) without touching business logic.

``DynamoDBRepository`` is the boto3-backed implementation. It is intentionally
free of business logic: it stores and retrieves items by key and does no
transformation beyond what DynamoDB storage requires (floats <-> ``Decimal``).
"""

import json
from decimal import Decimal
from typing import Any, Protocol

from src.core.database import get_resource


class Repository(Protocol):
    """Structural interface for key/value-ish persistence over one table."""

    def save(self, item: dict[str, Any]) -> dict[str, Any]:
        """Persist a complete item (create or full overwrite)."""
        ...  # pragma: no cover

    def get(self, key: str) -> dict[str, Any] | None:
        """Fetch a single item by its partition key."""
        ...  # pragma: no cover

    def list(self) -> list[dict[str, Any]]:
        """Return all items in the table."""
        ...  # pragma: no cover

    def update(self, key: str, item: dict[str, Any]) -> dict[str, Any]:
        """Overwrite the item at ``key`` with ``item`` (full replace)."""
        ...  # pragma: no cover

    def delete(self, key: str) -> bool:
        """Delete an item by key. Returns True if an item was deleted."""
        ...  # pragma: no cover


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
    """boto3-backed :class:`Repository` over a single DynamoDB table."""

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
