import aws_cdk as cdk
from aws_cdk import aws_dynamodb as dynamodb
from constructs import Construct

from .config import Config, expenses_table_name


class DatabaseStack(cdk.Stack):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        environment: str,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.table = dynamodb.Table(
            self,
            "ExpensesTable",
            table_name=expenses_table_name(environment),
            partition_key=dynamodb.Attribute(
                name=Config.PARTITION_KEY,
                type=dynamodb.AttributeType.STRING,
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=cdk.RemovalPolicy.DESTROY,
        )
