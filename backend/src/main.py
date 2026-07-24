"""Cashlytics backend — FastAPI app.

The same ``app`` object is used by local dev (uvicorn), the tests, and the
Lambda handler. Configuration is entirely env-var driven. Domain routes live in
their own packages (``src/expense``) and are included here.
"""

import logging
import os

from botocore.exceptions import ClientError
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.expense.controllers import router as expense_router
from src.reminder.controllers import router as reminder_router

logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"))
logger = logging.getLogger("cashlytics")

app = FastAPI(title="Cashlytics API")

# Equivalent to Flask's CORS(app): allow any origin.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(expense_router)
app.include_router(reminder_router)


@app.exception_handler(ClientError)
async def dynamodb_error_handler(request: Request, exc: ClientError) -> JSONResponse:
    """Translate storage (boto3) failures into a 503 instead of a raw 500.

    Applies to every route: any DynamoDB error raised by a repository — table
    missing, throttling, credentials — is logged with its stack trace and
    reported to the client without leaking AWS details.
    """
    logger.error("DynamoDB error on %s %s", request.method, request.url.path, exc_info=exc)
    return JSONResponse(
        status_code=503, content={"detail": "Storage temporarily unavailable"}
    )


@app.get("/")
def health() -> dict:
    """Health/info route."""
    return {"service": "cashlytics", "status": "ok"}
