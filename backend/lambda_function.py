"""AWS Lambda entrypoint for the Cashlytics backend.

Wraps the **same** FastAPI ``app`` used by local dev and the tests with Mangum,
so every route works unchanged behind an HTTP API / API Gateway / function URL.
No Lambda-only app is forked.

Deployed as a container image with ``CMD ["lambda_function.handler"]``.
"""

from mangum import Mangum

from src.main import app

handler = Mangum(app)
