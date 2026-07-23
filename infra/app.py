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

# Reminder domain (SMS via Sent.dm). Left empty for local/PR/dev deploys,
# which have no need to actually send messages; only prod deploys supply a
# real value, sourced from a GitHub secret, via -c. Recipients come from
# Cognito (each admin's phone_number attribute), not a context value.
sentdm_api_key: str = app.node.try_get_context("sentdm_api_key") or ""

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
