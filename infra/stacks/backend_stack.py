import os

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

        # The two administrator users. In prod, Cognito emails each user a
        # temporary password and the login page forces them to choose their own
        # (NEW_PASSWORD_REQUIRED). In non-prod the invitation is suppressed and
        # the deploy workflow sets the well-known dev password instead.
        for index, email in enumerate(admin_emails, start=1):
            user = cognito.CfnUserPoolUser(
                self,
                f"AdminUser{index}",
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
                f"AdminUser{index}GroupAttachment",
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

        # --- HTTP API with Cognito JWT authorizer ------------------------
        # Every route requires a valid Cognito JWT; the Lambda trusts the
        # claims API Gateway forwards in the request context and never
        # validates tokens itself.
        authorizer = apigwv2_authorizers.HttpUserPoolAuthorizer(
            "CognitoAuthorizer",
            user_pool,
            user_pool_clients=[user_pool_client],
        )

        http_api = apigwv2.HttpApi(
            self,
            "HttpApi",
            api_name=f"cashlytics-{environment}",
            default_authorizer=authorizer,
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

        # "/{proxy+}" does not match the bare root path, so both are added.
        http_api.add_routes(
            path="/",
            methods=[apigwv2.HttpMethod.ANY],
            integration=integration,
        )
        http_api.add_routes(
            path="/{proxy+}",
            methods=[apigwv2.HttpMethod.ANY],
            integration=integration,
        )

        self.http_api = http_api
        self.user_pool = user_pool
        self.user_pool_client = user_pool_client

        cdk.CfnOutput(self, "BackendUrl", value=http_api.url or "")
        cdk.CfnOutput(self, "UserPoolId", value=user_pool.user_pool_id)
        cdk.CfnOutput(
            self, "UserPoolClientId", value=user_pool_client.user_pool_client_id
        )
