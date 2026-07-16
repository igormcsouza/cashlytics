"""DynamoDB connection handling for the backend."""

from functools import lru_cache

import boto3

from src.core.config import aws_region, dynamodb_endpoint_url


@lru_cache(maxsize=1)
def get_resource():
    """DynamoDB resource, initialized once and cached (cold-start friendly)."""
    return boto3.resource(
        "dynamodb",
        region_name=aws_region(),
        endpoint_url=dynamodb_endpoint_url(),
    )
