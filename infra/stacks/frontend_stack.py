import os

import aws_cdk as cdk
from aws_cdk import aws_cloudfront as cloudfront
from aws_cdk import aws_cloudfront_origins as origins
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
        server_fn_dir = os.path.join(open_next_dir, "server-functions", "default")
        assets_dir = os.path.join(open_next_dir, "assets")

        # Phase-1 deploys (DB + backend only) synthesise this stack before the
        # OpenNext build exists — fall back to placeholder so synthesis doesn't
        # fail.  Phase-3 deletes cdk.out before re-deploying, forcing a fresh
        # synthesis where the real build is present.
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
                # OpenNext reads BUCKET_NAME to locate ISR cache in S3.
                "BUCKET_NAME": self.assets_bucket.bucket_name,
            },
        )

        self.assets_bucket.grant_read(fn)

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

        # CloudFront sits in front of both origins:
        #   /_next/static/*  →  S3 (private bucket via OAC, long-lived cache)
        #   everything else  →  Lambda Function URL (no cache, all methods)
        #
        # This is required because the S3 bucket is private; the browser cannot
        # fetch /_next/static/* directly — only CloudFront can, via OAC.
        s3_origin = origins.S3BucketOrigin.with_origin_access_control(
            self.assets_bucket
        )
        lambda_origin = origins.FunctionUrlOrigin(self.function_url)

        distribution = cloudfront.Distribution(
            self,
            "Distribution",
            default_behavior=cloudfront.BehaviorOptions(
                origin=lambda_origin,
                viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
                cache_policy=cloudfront.CachePolicy.CACHING_DISABLED,
                allowed_methods=cloudfront.AllowedMethods.ALLOW_ALL,
                origin_request_policy=cloudfront.OriginRequestPolicy.ALL_VIEWER_EXCEPT_HOST_HEADER,
            ),
            additional_behaviors={
                "/_next/static/*": cloudfront.BehaviorOptions(
                    origin=s3_origin,
                    viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
                    cache_policy=cloudfront.CachePolicy.CACHING_OPTIMIZED,
                ),
            },
        )

        cdk.CfnOutput(
            self,
            "FrontendUrl",
            value=f"https://{distribution.distribution_domain_name}",
        )
        cdk.CfnOutput(self, "AssetsBucketName", value=self.assets_bucket.bucket_name)
