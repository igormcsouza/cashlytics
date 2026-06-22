import os

import aws_cdk as cdk
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
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

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

        self.function_url = fn.add_function_url(
            auth_type=lambda_.FunctionUrlAuthType.NONE,
            cors=lambda_.FunctionUrlCorsOptions(
                allowed_origins=["*"],
            ),
        )

        cdk.CfnOutput(self, "BackendUrl", value=self.function_url.url)
