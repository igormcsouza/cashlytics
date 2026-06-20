#!/usr/bin/env node
import * as cdk from "aws-cdk-lib";
import { BackendStack } from "../lib/backend-stack";
import { DatabaseStack } from "../lib/database-stack";
import { FrontendStack } from "../lib/frontend-stack";

const app = new cdk.App();

const env = {
  account: process.env.CDK_DEFAULT_ACCOUNT,
  region: process.env.CDK_DEFAULT_REGION,
};

const database = new DatabaseStack(app, "CashlyticsDatabase", { env });

const backend = new BackendStack(app, "CashlyticsBackend", {
  env,
  table: database.table,
});

new FrontendStack(app, "CashlyticsFrontend", {
  env,
  apiBaseUrl: backend.functionUrl.url,
});
