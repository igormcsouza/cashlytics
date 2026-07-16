"""Create the local DynamoDB table the app and tests expect.

Run against DynamoDB Local in development:

    ENVIRONMENT=dev DYNAMODB_ENDPOINT_URL=http://localhost:8000 \
        uv run python -m src.core.bootstrap

The table name is composed as ``<ENVIRONMENT>-expenses`` (default ``dev``).
In AWS the table is provisioned by the CDK stacks, not this script.
"""

from src.core.config import table_name
from src.core.database import get_resource

EXPENSES_TABLE = table_name("expenses")


def create_table(name: str = EXPENSES_TABLE) -> None:
    """Create the expenses table with a string ``id`` partition key (idempotent)."""
    client = get_resource().meta.client
    existing = client.list_tables().get("TableNames", [])
    if name in existing:
        print(f"Table '{name}' already exists.")
        return
    client.create_table(
        TableName=name,
        KeySchema=[{"AttributeName": "id", "KeyType": "HASH"}],
        AttributeDefinitions=[{"AttributeName": "id", "AttributeType": "S"}],
        BillingMode="PAY_PER_REQUEST",
    )
    client.get_waiter("table_exists").wait(TableName=name)
    print(f"Created table '{name}'.")


if __name__ == "__main__":  # pragma: no cover
    create_table()
