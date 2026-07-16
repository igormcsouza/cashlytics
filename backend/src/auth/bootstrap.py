"""Create the local Cognito user pool the app expects (mirrors src/core/bootstrap.py).

Run against cognito-local in development:

    AWS_REGION=sa-east-1 COGNITO_ENDPOINT_URL=http://localhost:9229 \
        uv run python -m src.auth.bootstrap

Creates the "admin" group and a dev admin user with a permanent, well-known
password so local environments can log in immediately (mirrors what the
deploy workflow does against the real Cognito user pool). The pool's password
policy is relaxed (no complexity requirements) so the well-known dev password
is accepted — the same policy CDK gives non-prod user pools. Writes the
resulting pool/client ids to ``/local-shared/.cognito.env`` so the frontend
build (which needs them baked in at build time, like NEXT_PUBLIC_API_BASE_URL)
can pick them up.
"""

import os

import boto3

from src.auth.service import ADMIN_GROUP

POOL_NAME = "cashlytics-local"
CLIENT_NAME = "WebClient"
ADMIN_EMAILS = ["admin@cashlytics.dev"]
DEV_PASSWORD = "password"
OUTPUT_FILE = "/local-shared/.cognito.env"


def _client():
    region = os.environ.get("AWS_REGION", "sa-east-1")
    endpoint = os.environ.get("COGNITO_ENDPOINT_URL")
    return boto3.client("cognito-idp", region_name=region, endpoint_url=endpoint)


def _get_or_create_pool(client) -> str:
    for pool in client.list_user_pools(MaxResults=60)["UserPools"]:
        if pool["Name"] == POOL_NAME:
            return pool["Id"]
    created = client.create_user_pool(
        PoolName=POOL_NAME,
        Policies={
            "PasswordPolicy": {
                "MinimumLength": 8,
                "RequireUppercase": False,
                "RequireLowercase": False,
                "RequireNumbers": False,
                "RequireSymbols": False,
            }
        },
    )
    return created["UserPool"]["Id"]


def _get_or_create_client(client, pool_id: str) -> str:
    for app_client in client.list_user_pool_clients(
        UserPoolId=pool_id, MaxResults=60
    )["UserPoolClients"]:
        if app_client["ClientName"] == CLIENT_NAME:
            return app_client["ClientId"]
    return client.create_user_pool_client(
        UserPoolId=pool_id,
        ClientName=CLIENT_NAME,
        ExplicitAuthFlows=["ALLOW_USER_PASSWORD_AUTH", "ALLOW_REFRESH_TOKEN_AUTH"],
    )["UserPoolClient"]["ClientId"]


def _ensure_group(client, pool_id: str) -> None:
    try:
        client.create_group(UserPoolId=pool_id, GroupName=ADMIN_GROUP)
    except client.exceptions.GroupExistsException:
        pass


def _ensure_admin(client, pool_id: str, email: str) -> None:
    try:
        client.admin_create_user(
            UserPoolId=pool_id,
            Username=email,
            UserAttributes=[
                {"Name": "email", "Value": email},
                {"Name": "email_verified", "Value": "true"},
            ],
            MessageAction="SUPPRESS",
        )
    except client.exceptions.UsernameExistsException:
        pass
    client.admin_add_user_to_group(
        UserPoolId=pool_id, Username=email, GroupName=ADMIN_GROUP
    )
    client.admin_set_user_password(
        UserPoolId=pool_id, Username=email, Password=DEV_PASSWORD, Permanent=True
    )


def bootstrap() -> tuple[str, str]:
    """Ensure the pool/client/admins exist; return (pool_id, client_id)."""
    client = _client()
    pool_id = _get_or_create_pool(client)
    client_id = _get_or_create_client(client, pool_id)
    _ensure_group(client, pool_id)
    for email in ADMIN_EMAILS:
        _ensure_admin(client, pool_id, email)
    return pool_id, client_id


def main() -> None:
    pool_id, client_id = bootstrap()
    region = os.environ.get("AWS_REGION", "sa-east-1")

    with open(OUTPUT_FILE, "w") as f:
        f.write(f"NEXT_PUBLIC_COGNITO_CLIENT_ID={client_id}\n")
        f.write(f"NEXT_PUBLIC_COGNITO_REGION={region}\n")

    print(f"Cognito ready: pool={pool_id} client={client_id}")
    print(f"Dev admins: {', '.join(ADMIN_EMAILS)} / password: {DEV_PASSWORD}")


if __name__ == "__main__":  # pragma: no cover
    main()
