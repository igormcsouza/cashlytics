class Config:
    EXPENSES_TABLE_BASE_NAME = "expenses"
    EXPENSE_STATUS_TABLE_BASE_NAME = "expense-status"
    PARTITION_KEY = "id"
    DEFAULT_ENVIRONMENT = "dev"

    ENV_ENVIRONMENT = "ENVIRONMENT"
    ENV_DYNAMO_ENDPOINT = "DYNAMODB_ENDPOINT_URL"
    ENV_API_BASE_URL = "NEXT_PUBLIC_API_BASE_URL"

    # Cognito role with full access to the app. Must match ADMIN_GROUP in
    # backend/src/auth/services.py — separate, independently-deployed Python
    # projects, so this can't be a shared import; rename both or neither.
    ADMIN_GROUP = "admin"
    # Default admin users for non-prod environments; the deploy workflow sets
    # their password. Prod deploys override via `-c admin_emails=...`.
    DEFAULT_ADMIN_EMAILS = "admin@cashlytics.dev,admin2@cashlytics.dev"


def expenses_table_name(environment: str) -> str:
    return f"{environment}-{Config.EXPENSES_TABLE_BASE_NAME}"


def expense_status_table_name(environment: str) -> str:
    return f"{environment}-{Config.EXPENSE_STATUS_TABLE_BASE_NAME}"
