"""DynamoDB connection handling for the backend."""

from functools import lru_cache

import boto3

from src.core.config import AWS_REGION, DYNAMODB_ENDPOINT_URL


@lru_cache(maxsize=1)
def get_resource():
    """DynamoDB resource, initialized once at module scope (cold-start friendly)."""
    return boto3.resource(
        "dynamodb",
        region_name=AWS_REGION,
        endpoint_url=DYNAMODB_ENDPOINT_URL,
    )
