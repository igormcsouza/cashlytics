import os
import re

import aws_cdk as cdk
from aws_cdk import aws_apigatewayv2 as apigwv2
from aws_cdk import aws_apigatewayv2_authorizers as apigwv2_authorizers
from aws_cdk import aws_apigatewayv2_integrations as apigwv2_integrations
from aws_cdk import aws_cognito as cognito
from aws_cdk import aws_dynamodb as dynamodb
from aws_cdk import aws_lambda as lambda_
from constructs import Construct

from .config import Config


class BackendStack(cdk.Stack):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        table: dynamodb.Table,
        environment: str,
        admin_emails: list[str],
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        is_prod = environment == "prod"

        # --- Cognito -----------------------------------------------------
        # Email + password sign-in only, no self-sign-up. Non-prod pools use a
        # relaxed password policy so PR environments can use the well-known dev
        # password, and are destroyed with the stack.
        user_pool = cognito.UserPool(
            self,
            "UserPool",
            user_pool_name=f"cashlytics-{environment}",
            self_sign_up_enabled=False,
            sign_in_aliases=cognito.SignInAliases(email=True),
            account_recovery=cognito.AccountRecovery.EMAIL_ONLY,
            password_policy=(
                cognito.PasswordPolicy(
                    min_length=12,
                    require_lowercase=True,
                    require_uppercase=True,
                    require_digits=True,
                    require_symbols=True,
                )
                if is_prod
                else cognito.PasswordPolicy(
                    min_length=8,
                    require_lowercase=False,
                    require_uppercase=False,
                    require_digits=False,
                    require_symbols=False,
                )
            ),
            removal_policy=(
                cdk.RemovalPolicy.RETAIN if is_prod else cdk.RemovalPolicy.DESTROY
            ),
        )

        # Browser client: USER_PASSWORD_AUTH so the frontend can log in with a
        # plain fetch call (no SRP library), plus refresh tokens for silent
        # session renewal.
        user_pool_client = user_pool.add_client(
            "WebClient",
            auth_flows=cognito.AuthFlow(user_password=True),
            prevent_user_existence_errors=True,
        )

        admin_group = cognito.CfnUserPoolGroup(
            self,
            "AdminGroup",
            user_pool_id=user_pool.user_pool_id,
            group_name=Config.ADMIN_GROUP,
            description="Full access: see and update expenses.",
        )

        # The administrator users. In prod, Cognito emails each user a
        # temporary password and the login page forces them to choose their own
        # (NEW_PASSWORD_REQUIRED). In non-prod the invitation is suppressed and
        # the deploy workflow sets the well-known dev password instead.
        #
        # Construct ids are derived from the email itself, not its position in
        # admin_emails: Cognito usernames are immutable, so a stable id keyed
        # off the email keeps a reorder/insert/removal in the list from being
        # seen by CloudFormation as "this logical resource's username changed"
        # (which would attempt to replace an unrelated, already-provisioned
        # admin user).
        for email in admin_emails:
            construct_id = re.sub(r"[^A-Za-z0-9]", "", email)
            user = cognito.CfnUserPoolUser(
                self,
                f"AdminUser{construct_id}",
                user_pool_id=user_pool.user_pool_id,
                username=email,
                message_action=None if is_prod else "SUPPRESS",
                desired_delivery_mediums=["EMAIL"] if is_prod else None,
                user_attributes=[
                    cognito.CfnUserPoolUser.AttributeTypeProperty(
                        name="email", value=email
                    ),
                    cognito.CfnUserPoolUser.AttributeTypeProperty(
                        name="email_verified", value="true"
                    ),
                ],
            )
            attachment = cognito.CfnUserPoolUserToGroupAttachment(
                self,
                f"AdminUser{construct_id}GroupAttachment",
                user_pool_id=user_pool.user_pool_id,
                group_name=Config.ADMIN_GROUP,
                username=email,
            )
            attachment.add_dependency(user)
            attachment.add_dependency(admin_group)

        # --- Lambda ------------------------------------------------------
        backend_dir = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..", "backend")
        )

        fn = lambda_.DockerImageFunction(
            self,
            "BackendFunction",
            code=lambda_.DockerImageCode.from_image_asset(backend_dir),
            memory_size=512,
            timeout=cdk.Duration.seconds(30),
            environment={
                Config.ENV_ENVIRONMENT: environment,
            },
        )

        table.grant_read_write_data(fn)

        # Deliberately kept unused. The HTTP API below replaces this as the
        # public entrypoint, but the live CashlyticsFrontend-prod stack was
        # still importing this FunctionUrl's cross-stack export when the
        # switch to the HTTP API shipped, and CloudFormation refuses to
        # delete an export while another *currently deployed* stack imports
        # it. Re-adding the resource alone isn't enough: CDK only emits the
        # export when some other stack in the app still references it, and
        # nothing does anymore now that the frontend uses http_api.url — so
        # the export gets dropped from the template regardless, and the
        # deploy still fails (see PR #20's followup). The explicit
        # `export_name`/`CfnOutput` below pins the export in place
        # independent of any in-app consumer, matching the exact name CDK
        # auto-generated originally, so this stack's template is a genuine
        # no-op for that export and the deploy stops failing.
        #
        # Safe to delete both the resource and this Output once a frontend
        # deploy has gone out on top of this commit (frontend no longer
        # imports it, so nothing will be left holding the export).
        legacy_function_url = fn.add_function_url(
            auth_type=lambda_.FunctionUrlAuthType.NONE
        )
        if is_prod:
            cdk.CfnOutput(
                self,
                "ExportsOutputFnGetAttBackendFunctionFunctionUrl9AC67B19FunctionUrl8F87D627",
                value=legacy_function_url.url,
                export_name=(
                    f"CashlyticsBackend-{environment}:"
                    "ExportsOutputFnGetAttBackendFunctionFunctionUrl9AC67B19"
                    "FunctionUrl8F87D627"
                ),
            )

        # --- HTTP API with Cognito JWT authorizer ------------------------
        # Every /expenses* route requires a valid Cognito JWT; the Lambda
        # trusts the claims API Gateway forwards in the request context and
        # never validates tokens itself. "/" (the health route) is
        # deliberately left public — see below.
        authorizer = apigwv2_authorizers.HttpUserPoolAuthorizer(
            "CognitoAuthorizer",
            user_pool,
            user_pool_clients=[user_pool_client],
        )

        http_api = apigwv2.HttpApi(
            self,
            "HttpApi",
            api_name=f"cashlytics-{environment}",
            cors_preflight=apigwv2.CorsPreflightOptions(
                allow_origins=["*"],
                allow_headers=["Authorization", "Content-Type"],
                allow_methods=[
                    apigwv2.CorsHttpMethod.GET,
                    apigwv2.CorsHttpMethod.POST,
                    apigwv2.CorsHttpMethod.PUT,
                    apigwv2.CorsHttpMethod.DELETE,
                    apigwv2.CorsHttpMethod.OPTIONS,
                ],
            ),
        )

        integration = apigwv2_integrations.HttpLambdaIntegration("Backend", fn)

        # Real HTTP methods only — OPTIONS is deliberately excluded so preflight
        # requests fall through to API Gateway's built-in CORS auto-response
        # (configured above) instead of being matched by these routes and
        # sent through the JWT authorizer, which browsers never attach
        # credentials to and would fail as a result. HEAD is included: it's a
        # real client request (some health checks send it instead of GET to
        # save bandwidth) that does carry credentials, unlike OPTIONS.
        route_methods = [
            apigwv2.HttpMethod.GET,
            apigwv2.HttpMethod.HEAD,
            apigwv2.HttpMethod.POST,
            apigwv2.HttpMethod.PUT,
            apigwv2.HttpMethod.DELETE,
        ]

        # Public paths: the health route, plus FastAPI's auto-generated API
        # docs (Swagger UI, ReDoc, and the raw OpenAPI schema they render).
        # Docs are just endpoint/schema metadata, not data — no reason to
        # require login to browse them, and Swagger's own "Try it out" still
        # needs a real token to call anything protected. No
        # default_authorizer is set on the API, so each is explicitly public
        # here; API Gateway matches these exact paths before falling through
        # to the "/{proxy+}" catch-all below.
        public_paths = ["/", "/docs", "/redoc", "/openapi.json"]
        for path in public_paths:
            http_api.add_routes(
                path=path,
                methods=route_methods,
                integration=integration,
                authorizer=apigwv2.HttpNoneAuthorizer(),
            )

        # Everything else goes through "/{proxy+}", explicitly authorized,
        # which in practice is everything under /expenses.
        http_api.add_routes(
            path="/{proxy+}",
            methods=route_methods,
            integration=integration,
            authorizer=authorizer,
        )

        self.http_api = http_api
        self.user_pool = user_pool
        self.user_pool_client = user_pool_client

        cdk.CfnOutput(self, "BackendUrl", value=http_api.url or "")
        cdk.CfnOutput(self, "UserPoolId", value=user_pool.user_pool_id)
        cdk.CfnOutput(
            self, "UserPoolClientId", value=user_pool_client.user_pool_client_id
        )
