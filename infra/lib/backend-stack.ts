import * as path from "path";
import * as cdk from "aws-cdk-lib";
import * as dynamodb from "aws-cdk-lib/aws-dynamodb";
import * as lambda from "aws-cdk-lib/aws-lambda";
import { Construct } from "constructs";
import { config } from "./config";

interface BackendStackProps extends cdk.StackProps {
  table: dynamodb.Table;
  environment: string;
}

/**
 * The backend Lambda, built from the Step 3 container image
 * (`lambda_function.handler`) and fronted by a function URL.
 *
 * Note on AWS_REGION: the Lambda runtime injects AWS_REGION automatically — it
 * is a reserved env var and cannot be set on the function — so the backend
 * reads it at runtime without us configuring it here. DYNAMODB_ENDPOINT_URL is
 * intentionally NOT set so the SDK targets the real DynamoDB endpoint in AWS.
 */
export class BackendStack extends cdk.Stack {
  public readonly functionUrl: lambda.FunctionUrl;

  constructor(scope: Construct, id: string, props: BackendStackProps) {
    super(scope, id, props);

    const fn = new lambda.DockerImageFunction(this, "BackendFunction", {
      code: lambda.DockerImageCode.fromImageAsset(
        path.join(__dirname, "..", "..", "backend"),
      ),
      memorySize: 512,
      timeout: cdk.Duration.seconds(30),
      environment: {
        [config.envEnvironment]: props.environment,
      },
    });

    // Least-privilege read/write on the expenses table only.
    props.table.grantReadWriteData(fn);

    this.functionUrl = fn.addFunctionUrl({
      authType: lambda.FunctionUrlAuthType.NONE,
      cors: { allowedOrigins: ["*"] },
    });

    new cdk.CfnOutput(this, "BackendUrl", { value: this.functionUrl.url });
  }
}
