"""Create and seed the local DynamoDB table the app and tests expect.

Run against DynamoDB Local in development:

    ENVIRONMENT=dev DYNAMODB_ENDPOINT_URL=http://localhost:8000 \
        uv run python -m src.core.bootstrap

The table name is composed as ``<ENVIRONMENT>-expenses`` (default ``dev``).
In AWS the table is provisioned by the CDK stacks, not this script.

Seeding: ``seed_data.json`` (sample expenses with stable ``seed-*`` ids, so
re-running never duplicates) is loaded **only** when ``ENVIRONMENT`` is one of
``SEED_ENVIRONMENTS`` — never in stage/prod.
"""

import json
import os
from pathlib import Path

from src.core.config import table_name
from src.core.database import get_resource
from src.shared.repository import DynamoDBRepository

EXPENSES_TABLE = table_name("expenses")

SEED_ENVIRONMENTS = ("dev", "local")
SEED_FILE = Path(__file__).with_name("seed_data.json")


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


def seed_table(name: str = EXPENSES_TABLE) -> None:
    """Load sample expenses from ``seed_data.json`` — development/local ONLY.

    Guarded by ``ENVIRONMENT``: any other value (stage, prod, test, pr-*) is a
    no-op, so production data can never be polluted. Idempotent: seed items
    have stable ids, so re-running overwrites them instead of duplicating.
    """
    environment = os.environ.get("ENVIRONMENT", "dev")
    if environment not in SEED_ENVIRONMENTS:
        print(f"Skipping seed data: environment '{environment}' is not one of {SEED_ENVIRONMENTS}.")
        return
    repository = DynamoDBRepository(name)
    items = json.loads(SEED_FILE.read_text())
    for item in items:
        repository.save(item)
    print(f"Seeded {len(items)} sample expenses into '{name}'.")


if __name__ == "__main__":  # pragma: no cover
    create_table()
    seed_table()
