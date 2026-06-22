#!/usr/bin/env node
import * as cdk from "aws-cdk-lib";
import { BackendStack } from "../lib/backend-stack";
import { DatabaseStack } from "../lib/database-stack";
import { FrontendStack } from "../lib/frontend-stack";
import { config } from "../lib/config";

const app = new cdk.App();

const env = {
  account: process.env.CDK_DEFAULT_ACCOUNT,
  region: process.env.CDK_DEFAULT_REGION,
};

// Deployment environment (dev/stage/prod) drives table naming. Override with
// `cdk deploy -c environment=prod`.
const environment =
  (app.node.tryGetContext("environment") as string | undefined) ??
  config.defaultEnvironment;

const database = new DatabaseStack(app, "CashlyticsDatabase", {
  env,
  environment,
});

const backend = new BackendStack(app, "CashlyticsBackend", {
  env,
  table: database.table,
  environment,
});

new FrontendStack(app, "CashlyticsFrontend", {
  env,
  apiBaseUrl: backend.functionUrl.url,
});
