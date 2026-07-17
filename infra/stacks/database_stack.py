import aws_cdk as cdk
from aws_cdk import aws_dynamodb as dynamodb
from constructs import Construct

from .config import Config, expense_status_table_name, expenses_table_name


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

        # Per-month paid/due status for recurring expense instances (issue #10):
        # keyed by a composite "{expense_id}#{month}" id so a recurring
        # expense's paid status is tracked independently for every month it
        # recurs into.
        self.status_table = dynamodb.Table(
            self,
            "ExpenseStatusTable",
            table_name=expense_status_table_name(environment),
            partition_key=dynamodb.Attribute(
                name=Config.PARTITION_KEY,
                type=dynamodb.AttributeType.STRING,
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=cdk.RemovalPolicy.DESTROY,
        )
