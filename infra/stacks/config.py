class Config:
    EXPENSES_TABLE_BASE_NAME = "expenses"
    PARTITION_KEY = "id"
    DEFAULT_ENVIRONMENT = "dev"

    ENV_ENVIRONMENT = "ENVIRONMENT"
    ENV_DYNAMO_ENDPOINT = "DYNAMODB_ENDPOINT_URL"
    ENV_API_BASE_URL = "NEXT_PUBLIC_API_BASE_URL"


def expenses_table_name(environment: str) -> str:
    return f"{environment}-{Config.EXPENSES_TABLE_BASE_NAME}"
