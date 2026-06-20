"""Create the local DynamoDB table the app and tests expect.

Run against DynamoDB Local in development:

    EXPENSES_TABLE=expenses DYNAMODB_ENDPOINT_URL=http://localhost:8000 \
        uv run python -m database.bootstrap

In AWS the table is provisioned by the CDK stacks (Step 5), not this script.
"""

import os

from database.repository import get_resource

EXPENSES_TABLE = os.environ.get("EXPENSES_TABLE", "expenses")


def create_table(table_name: str = EXPENSES_TABLE) -> None:
    """Create the expenses table with a string ``id`` partition key (idempotent)."""
    client = get_resource().meta.client
    existing = client.list_tables().get("TableNames", [])
    if table_name in existing:
        print(f"Table '{table_name}' already exists.")
        return
    client.create_table(
        TableName=table_name,
        KeySchema=[{"AttributeName": "id", "KeyType": "HASH"}],
        AttributeDefinitions=[{"AttributeName": "id", "AttributeType": "S"}],
        BillingMode="PAY_PER_REQUEST",
    )
    client.get_waiter("table_exists").wait(TableName=table_name)
    print(f"Created table '{table_name}'.")


if __name__ == "__main__":
    create_table()
