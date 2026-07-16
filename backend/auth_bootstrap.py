"""Create the local Cognito user pool the app expects (mirrors database/bootstrap.py).

Run against cognito-local in development:

    AWS_REGION=us-east-1 COGNITO_ENDPOINT_URL=http://localhost:9229 \
        uv run python -m auth_bootstrap

Creates the "admin" group and two dev admin users with a permanent, well-known
password so PR/local environments can log in immediately (mirrors what the
deploy workflow does against the real Cognito user pool). Writes the
resulting pool/client ids to ``/local-shared/.cognito.env`` so the frontend
build (which needs them baked in at build time, like NEXT_PUBLIC_API_BASE_URL)
can pick them up.
"""

import os

import boto3

from auth import ADMIN_GROUP

POOL_NAME = "cashlytics-local"
CLIENT_NAME = "WebClient"
ADMIN_EMAILS = ["admin@cashlytics.dev", "admin2@cashlytics.dev"]
DEV_PASSWORD = "password"
OUTPUT_FILE = "/local-shared/.cognito.env"

REGION = os.environ.get("AWS_REGION", "us-east-1")
ENDPOINT = os.environ.get("COGNITO_ENDPOINT_URL")


def _client():
    return boto3.client("cognito-idp", region_name=REGION, endpoint_url=ENDPOINT)


def _get_or_create_pool(client) -> str:
    for pool in client.list_user_pools(MaxResults=60)["UserPools"]:
        if pool["Name"] == POOL_NAME:
            return pool["Id"]
    return client.create_user_pool(PoolName=POOL_NAME)["UserPool"]["Id"]


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


def main() -> None:
    client = _client()
    pool_id = _get_or_create_pool(client)
    client_id = _get_or_create_client(client, pool_id)
    _ensure_group(client, pool_id)
    for email in ADMIN_EMAILS:
        _ensure_admin(client, pool_id, email)

    with open(OUTPUT_FILE, "w") as f:
        f.write(f"NEXT_PUBLIC_COGNITO_CLIENT_ID={client_id}\n")
        f.write(f"NEXT_PUBLIC_COGNITO_REGION={REGION}\n")

    print(f"Cognito ready: pool={pool_id} client={client_id}")
    print(f"Dev admins: {', '.join(ADMIN_EMAILS)} / password: {DEV_PASSWORD}")


if __name__ == "__main__":
    main()
