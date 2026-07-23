"""AWS Lambda entrypoint for the daily WhatsApp reminder job.

Triggered by an EventBridge scheduled rule (see ``ReminderFunction`` in
``infra/stacks/backend_stack.py``), not API Gateway — no Mangum wrapping here,
this is a plain Lambda handler.

Deployed as the same container image as ``lambda_function.py``, with
``CMD ["reminder_lambda_function.handler"]`` overridden per-function in CDK.
"""

from src.reminder.services import get_reminder_service


def handler(event, context):
    result = get_reminder_service().run()
    return result.model_dump()
