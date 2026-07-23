"""Tests for the reminder Lambda handler.

Invoked directly as a plain function call — unlike lambda_function.py this
isn't wrapped by Mangum, since it's triggered by an EventBridge scheduled
rule, not API Gateway. Uses moto-backed DynamoDB (via the ``dynamodb_table``
fixture), no real AWS or Sent.dm call.
"""


def test_handler_no_expenses_due_sends_nothing(dynamodb_table):
    from reminder_lambda_function import handler

    result = handler({}, None)

    assert result == {"sent": False, "expense_ids": []}
