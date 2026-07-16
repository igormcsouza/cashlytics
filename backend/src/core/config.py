"""Environment-driven configuration for the backend.

Everything is read from environment variables so the same code runs against
DynamoDB Local in dev and real DynamoDB in AWS.

Environment variables:
    AWS_REGION             AWS region (default: us-east-1)
    DYNAMODB_ENDPOINT_URL  Endpoint override for DynamoDB Local (unset in AWS)
    ENVIRONMENT            Deployment environment, prefixed to table names
                           (default: dev), e.g. ``prod`` -> ``prod-expenses``
"""

import os

AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")
DYNAMODB_ENDPOINT_URL = os.environ.get("DYNAMODB_ENDPOINT_URL")


def table_name(base: str) -> str:
    """Compose a fully-qualified table name from the deployment environment.

    The environment (``dev``/``stage``/``prod``) is read from the ``ENVIRONMENT``
    env var and prefixed to a hardcoded base name, e.g. ``prod`` + ``expenses``
    -> ``prod-expenses``. This keeps a single env var per deployment instead of
    one full table name per table, so adding tables doesn't add env vars.
    """
    environment = os.environ.get("ENVIRONMENT", "dev")
    return f"{environment}-{base}"
