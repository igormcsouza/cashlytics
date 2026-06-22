import * as cdk from "aws-cdk-lib";
import * as dynamodb from "aws-cdk-lib/aws-dynamodb";
import { Construct } from "constructs";
import { config, expensesTableName } from "./config";

interface DatabaseStackProps extends cdk.StackProps {
  environment: string;
}

/**
 * DynamoDB table for expenses, with a string `id` partition key. The table name
 * is composed as `<environment>-expenses`; the backend derives the same name
 * from the ENVIRONMENT env var (BackendStack).
 */
export class DatabaseStack extends cdk.Stack {
  public readonly table: dynamodb.Table;

  constructor(scope: Construct, id: string, props: DatabaseStackProps) {
    super(scope, id, props);

    this.table = new dynamodb.Table(this, "ExpensesTable", {
      tableName: expensesTableName(props.environment),
      partitionKey: {
        name: config.partitionKey,
        type: dynamodb.AttributeType.STRING,
      },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      removalPolicy: cdk.RemovalPolicy.DESTROY,
    });
  }
}
