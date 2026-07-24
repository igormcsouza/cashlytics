#!/usr/bin/env python3
import os

import aws_cdk as cdk

from stacks.backend_stack import BackendStack
from stacks.config import Config
from stacks.database_stack import DatabaseStack
from stacks.frontend_stack import FrontendStack

app = cdk.App()

env = cdk.Environment(
    account=os.environ.get("CDK_DEFAULT_ACCOUNT"),
    region=os.environ.get("CDK_DEFAULT_REGION"),
)

environment: str = app.node.try_get_context("environment") or Config.DEFAULT_ENVIRONMENT

admin_emails: list[str] = [
    email.strip()
    for email in (
        app.node.try_get_context("admin_emails") or Config.DEFAULT_ADMIN_EMAILS
    ).split(",")
    if email.strip()
]

# Reminder domain (SMS via Sent.dm). Sourced from the same repo-level GitHub
# secrets in both deploy-prod.yml and deploy-dev.yml (PR environments), via
# -c; empty only for local dev where nothing exercises the reminder job.
# Recipients come from Cognito (each admin's phone_number attribute), not a
# context value.
sentdm_api_key: str = app.node.try_get_context("sentdm_api_key") or ""
sentdm_template_id: str = app.node.try_get_context("sentdm_template_id") or ""

database = DatabaseStack(
    app,
    f"CashlyticsDatabase-{environment}",
    environment=environment,
    env=env,
)

backend = BackendStack(
    app,
    f"CashlyticsBackend-{environment}",
    table=database.table,
    status_table=database.status_table,
    environment=environment,
    admin_emails=admin_emails,
    sentdm_api_key=sentdm_api_key,
    sentdm_template_id=sentdm_template_id,
    env=env,
)

FrontendStack(
    app,
    f"CashlyticsFrontend-{environment}",
    api_base_url=backend.http_api.url or "",
    environment=environment,
    env=env,
)

app.synth()
