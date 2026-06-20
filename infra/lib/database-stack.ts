import * as cdk from "aws-cdk-lib";
import * as dynamodb from "aws-cdk-lib/aws-dynamodb";
import { Construct } from "constructs";
import { config } from "./config";

/**
 * DynamoDB table for expenses, with a string `id` partition key. The table name
 * is surfaced to the backend Lambda via the EXPENSES_TABLE env var (BackendStack).
 */
export class DatabaseStack extends cdk.Stack {
  public readonly table: dynamodb.Table;

  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    this.table = new dynamodb.Table(this, "ExpensesTable", {
      tableName: config.expensesTableName,
      partitionKey: {
        name: config.partitionKey,
        type: dynamodb.AttributeType.STRING,
      },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      removalPolicy: cdk.RemovalPolicy.DESTROY,
    });
  }
}
