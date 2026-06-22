import os

import aws_cdk as cdk
from aws_cdk import aws_lambda as lambda_
from aws_cdk import aws_s3 as s3
from aws_cdk import aws_s3_deployment as s3deploy
from constructs import Construct

from .config import Config

# Served while the real OpenNext bundle hasn't been built yet.
_PLACEHOLDER = (
    "exports.handler = async () => ({"
    " statusCode: 200,"
    " headers: { 'content-type': 'text/html' },"
    " body: '<html><body><h1>Cashlytics is deploying…</h1></body></html>' });"
)


class FrontendStack(cdk.Stack):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        api_base_url: str,
        environment: str,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.assets_bucket = s3.Bucket(
            self,
            "FrontendAssets",
            removal_policy=cdk.RemovalPolicy.DESTROY,
            auto_delete_objects=True,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            encryption=s3.BucketEncryption.S3_MANAGED,
        )

        open_next_dir = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..", "frontend", ".open-next")
        )
        server_fn_dir = os.path.join(open_next_dir, "server-function")
        assets_dir = os.path.join(open_next_dir, "assets")

        # Phase-1 deploys (DB + backend only) synthesise this stack before the
        # OpenNext build exists, so fall back to a placeholder so synthesis
        # doesn't fail.  Phase-3 deletes cdk.out before re-deploying, which
        # forces a fresh synthesis where the real build is present.
        if os.path.isdir(server_fn_dir):
            print(f"[FrontendStack] Using OpenNext build: {server_fn_dir}")
            fn_code: lambda_.Code = lambda_.Code.from_asset(server_fn_dir)
        else:
            print(f"[FrontendStack] WARNING: OpenNext build not found at {server_fn_dir} — using placeholder")
            fn_code = lambda_.Code.from_inline(_PLACEHOLDER)

        fn = lambda_.Function(
            self,
            "FrontendFunction",
            runtime=lambda_.Runtime.NODEJS_20_X,
            handler="index.handler",
            code=fn_code,
            memory_size=1024,
            timeout=cdk.Duration.seconds(30),
            environment={
                Config.ENV_API_BASE_URL: api_base_url,
            },
        )

        self.assets_bucket.grant_read(fn)

        # Upload OpenNext static assets to S3 when the build output exists.
        if os.path.isdir(assets_dir):
            s3deploy.BucketDeployment(
                self,
                "StaticAssets",
                sources=[s3deploy.Source.asset(assets_dir)],
                destination_bucket=self.assets_bucket,
            )

        self.function_url = fn.add_function_url(
            auth_type=lambda_.FunctionUrlAuthType.NONE,
        )

        cdk.CfnOutput(self, "FrontendUrl", value=self.function_url.url)
        cdk.CfnOutput(self, "AssetsBucketName", value=self.assets_bucket.bucket_name)
