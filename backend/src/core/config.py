"""Environment-driven configuration for the backend.

Everything is read from environment variables so the same code runs against
DynamoDB Local in dev and real DynamoDB in AWS.

Environment variables:
    AWS_REGION             AWS region (default: sa-east-1)
    DYNAMODB_ENDPOINT_URL  Endpoint override for DynamoDB Local (unset in AWS)
    ENVIRONMENT            Deployment environment, prefixed to table names
                           (default: dev), e.g. ``prod`` -> ``prod-expenses``
    SENTDM_API_KEY         Sent.dm API key (reminder domain)
    SENTDM_TEMPLATE_ID     Sent.dm WhatsApp template id (reminder domain)
    COGNITO_USER_POOL_ID   Cognito user pool id (reminder domain reads each
                           admin's phone_number attribute from this pool)

Values are read lazily (at call time, not import time) so tests and tooling can
adjust the environment without re-importing modules.
"""

import os


def aws_region() -> str:
    """AWS region for all SDK clients (default: São Paulo)."""
    return os.environ.get("AWS_REGION", "sa-east-1")


def dynamodb_endpoint_url() -> str | None:
    """DynamoDB endpoint override for DynamoDB Local; ``None`` in AWS."""
    return os.environ.get("DYNAMODB_ENDPOINT_URL")


def table_name(base: str) -> str:
    """Compose a fully-qualified table name from the deployment environment.

    The environment (``dev``/``stage``/``prod``) is read from the ``ENVIRONMENT``
    env var and prefixed to a hardcoded base name, e.g. ``prod`` + ``expenses``
    -> ``prod-expenses``. This keeps a single env var per deployment instead of
    one full table name per table, so adding tables doesn't add env vars.
    """
    environment = os.environ.get("ENVIRONMENT", "dev")
    return f"{environment}-{base}"


def sentdm_api_key() -> str:
    """Sent.dm API key, sent as the ``x-api-key`` header."""
    return os.environ.get("SENTDM_API_KEY", "")


def sentdm_template_id() -> str:
    """Sent.dm WhatsApp template id used for the daily reminder message."""
    return os.environ.get("SENTDM_TEMPLATE_ID", "")


def cognito_user_pool_id() -> str:
    """Cognito user pool id the reminder domain reads admin phone numbers from."""
    return os.environ.get("COGNITO_USER_POOL_ID", "")
