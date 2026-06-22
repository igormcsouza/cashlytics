/**
 * Single source of truth for names and env var keys, kept identical to the
 * application code (Step 3) and the local environment (Step 6).
 */
export const config = {
  // DynamoDB
  expensesTableBaseName: "expenses",
  partitionKey: "id",

  // Deployment environment (dev/stage/prod). Default when none is given on the
  // CDK context (`-c environment=prod`).
  defaultEnvironment: "dev",

  // Env var names read by the backend / frontend code
  envEnvironment: "ENVIRONMENT",
  envDynamoEndpoint: "DYNAMODB_ENDPOINT_URL",
  envApiBaseUrl: "NEXT_PUBLIC_API_BASE_URL",
} as const;

/**
 * Fully-qualified table name for a deployment environment, prefixing the
 * hardcoded base name, e.g. `prod` -> `prod-expenses`. Kept identical to the
 * backend's `table_name()` helper so both sides agree from one env var.
 */
export function expensesTableName(environment: string): string {
  return `${environment}-${config.expensesTableBaseName}`;
}
