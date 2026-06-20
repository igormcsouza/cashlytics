/**
 * Single source of truth for names and env var keys, kept identical to the
 * application code (Step 3) and the local environment (Step 6).
 */
export const config = {
  // DynamoDB
  expensesTableName: "cashlytics-expenses",
  partitionKey: "id",

  // Env var names read by the backend / frontend code
  envExpensesTable: "EXPENSES_TABLE",
  envDynamoEndpoint: "DYNAMODB_ENDPOINT_URL",
  envApiBaseUrl: "NEXT_PUBLIC_API_BASE_URL",
} as const;
