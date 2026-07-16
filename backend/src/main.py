"""Cashlytics backend — FastAPI app.

The same ``app`` object is used by local dev (uvicorn), the tests, and the
Lambda handler. Configuration is entirely env-var driven. Domain routes live in
their own packages (``src/expense``) and are included here.
"""

import logging
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.expense.controllers import router as expense_router

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


@app.get("/")
def health() -> dict:
    """Health/info route."""
    return {"service": "cashlytics", "status": "ok"}


if __name__ == "__main__":  # pragma: no cover
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", "5000")))
