import * as cdk from "aws-cdk-lib";
import * as lambda from "aws-cdk-lib/aws-lambda";
import * as s3 from "aws-cdk-lib/aws-s3";
import { Construct } from "constructs";
import { config } from "./config";

interface FrontendStackProps extends cdk.StackProps {
  /** Backend API base URL, injected into the frontend as NEXT_PUBLIC_API_BASE_URL. */
  apiBaseUrl: string;
}

/**
 * The Next.js frontend: an AWS Lambda function (server-rendered) plus an S3
 * bucket for static assets.
 *
 * Trade-off: packaging a full server-rendered Next.js build for Lambda (e.g.
 * via OpenNext) is a build concern outside this IaC. This stack provisions the
 * production-shaped resources — the SSR Lambda and the static-assets bucket —
 * with a placeholder handler; swap in the real bundle at deploy time.
 */
export class FrontendStack extends cdk.Stack {
  public readonly functionUrl: lambda.FunctionUrl;
  public readonly assetsBucket: s3.Bucket;

  constructor(scope: Construct, id: string, props: FrontendStackProps) {
    super(scope, id, props);

    this.assetsBucket = new s3.Bucket(this, "FrontendAssets", {
      removalPolicy: cdk.RemovalPolicy.DESTROY,
      autoDeleteObjects: true,
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
      encryption: s3.BucketEncryption.S3_MANAGED,
    });

    const fn = new lambda.Function(this, "FrontendFunction", {
      runtime: lambda.Runtime.NODEJS_20_X,
      handler: "index.handler",
      code: lambda.Code.fromInline(
        "exports.handler = async () => ({ statusCode: 200, headers: { 'content-type': 'text/plain' }, body: 'Cashlytics frontend (SSR placeholder)' });",
      ),
      memorySize: 512,
      timeout: cdk.Duration.seconds(30),
      environment: {
        [config.envApiBaseUrl]: props.apiBaseUrl,
      },
    });

    this.assetsBucket.grantRead(fn);

    this.functionUrl = fn.addFunctionUrl({
      authType: lambda.FunctionUrlAuthType.NONE,
    });

    new cdk.CfnOutput(this, "FrontendUrl", { value: this.functionUrl.url });
    new cdk.CfnOutput(this, "AssetsBucketName", {
      value: this.assetsBucket.bucketName,
    });
  }
}
