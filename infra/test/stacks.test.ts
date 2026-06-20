import * as cdk from "aws-cdk-lib";
import { Match, Template } from "aws-cdk-lib/assertions";
import { beforeAll, describe, expect, it } from "vitest";
import { BackendStack } from "../lib/backend-stack";
import { config } from "../lib/config";
import { DatabaseStack } from "../lib/database-stack";
import { FrontendStack } from "../lib/frontend-stack";

describe("DatabaseStack", () => {
  let template: Template;

  beforeAll(() => {
    const app = new cdk.App();
    const stack = new DatabaseStack(app, "TestDatabase");
    template = Template.fromStack(stack);
  });

  it("defines a DynamoDB table with an `id` string partition key", () => {
    template.hasResourceProperties("AWS::DynamoDB::Table", {
      TableName: config.expensesTableName,
      KeySchema: [{ AttributeName: "id", KeyType: "HASH" }],
      AttributeDefinitions: Match.arrayWith([
        { AttributeName: "id", AttributeType: "S" },
      ]),
    });
  });
});

describe("BackendStack", () => {
  let template: Template;

  beforeAll(() => {
    const app = new cdk.App();
    const database = new DatabaseStack(app, "TestDatabase");
    const backend = new BackendStack(app, "TestBackend", {
      table: database.table,
    });
    template = Template.fromStack(backend);
  });

  it("defines a container-image Lambda with the EXPENSES_TABLE env var", () => {
    template.hasResourceProperties("AWS::Lambda::Function", {
      PackageType: "Image",
      Environment: {
        Variables: Match.objectLike({
          // Value is a cross-stack reference to the table name.
          [config.envExpensesTable]: Match.anyValue(),
        }),
      },
    });
  });

  it("does not set DYNAMODB_ENDPOINT_URL or AWS_REGION (reserved)", () => {
    const fns = template.findResources("AWS::Lambda::Function");
    const vars = Object.values(fns)[0].Properties.Environment.Variables;
    expect(vars).not.toHaveProperty(config.envDynamoEndpoint);
    expect(vars).not.toHaveProperty("AWS_REGION");
  });

  it("grants the Lambda read/write on the expenses table", () => {
    const policies = template.findResources("AWS::IAM::Policy");
    const actions = Object.values(policies).flatMap((p: any) =>
      p.Properties.PolicyDocument.Statement.flatMap((s: any) =>
        Array.isArray(s.Action) ? s.Action : [s.Action],
      ),
    );
    for (const required of [
      "dynamodb:PutItem",
      "dynamodb:GetItem",
      "dynamodb:DeleteItem",
      "dynamodb:UpdateItem",
      "dynamodb:Scan",
    ]) {
      expect(actions).toContain(required);
    }
  });

  it("exposes the backend through a function URL", () => {
    template.resourceCountIs("AWS::Lambda::Url", 1);
  });
});

describe("FrontendStack", () => {
  let template: Template;

  beforeAll(() => {
    const app = new cdk.App();
    const stack = new FrontendStack(app, "TestFrontend", {
      apiBaseUrl: "https://backend.example.com/",
    });
    template = Template.fromStack(stack);
  });

  it("defines an SSR Lambda with the NEXT_PUBLIC_API_BASE_URL env var", () => {
    template.hasResourceProperties("AWS::Lambda::Function", {
      Handler: "index.handler",
      Runtime: "nodejs20.x",
      Environment: {
        Variables: Match.objectLike({
          [config.envApiBaseUrl]: "https://backend.example.com/",
        }),
      },
    });
  });

  it("defines an S3 bucket for static assets", () => {
    template.resourceCountIs("AWS::S3::Bucket", 1);
  });
});
