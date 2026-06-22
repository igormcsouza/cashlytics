"""Cashlytics backend — FastAPI app.

Persists expenses to DynamoDB through a generic repository (Step 2). The same
``app`` object is used by local dev (uvicorn), the tests, and the Lambda
handler. Configuration is entirely env-var driven.
"""

import logging
import os

from fastapi import Depends, FastAPI, HTTPException, Response, status
from fastapi.middleware.cors import CORSMiddleware

from database.models import Expense
from database.repository import DynamoDBRepository, table_name
from models import ExpenseIn

logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"))
logger = logging.getLogger("cashlytics")

EXPENSES_TABLE = table_name("expenses")

app = FastAPI(title="Cashlytics API")

# Equivalent to Flask's CORS(app): allow any origin.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_repository() -> DynamoDBRepository:
    """FastAPI dependency for the expenses repository.

    Overridable in tests via ``app.dependency_overrides``.
    """
    return DynamoDBRepository(EXPENSES_TABLE)


@app.get("/")
def health() -> dict:
    """Health/info route.

    The product UI is now the Next.js app under ``frontend/``; this backend no
    longer serves the superseded static Vue page.
    """
    return {"service": "cashlytics", "status": "ok"}


@app.get("/expenses")
def get_expenses(repo: DynamoDBRepository = Depends(get_repository)) -> list[dict]:
    return repo.list()


@app.post("/expenses", status_code=status.HTTP_201_CREATED)
def create_expense(
    expense: ExpenseIn, repo: DynamoDBRepository = Depends(get_repository)
) -> dict:
    created = Expense(**expense.model_dump())
    return repo.save(created.model_dump())


@app.put("/expenses/{expense_id}")
def update_expense(
    expense_id: str,
    expense: ExpenseIn,
    repo: DynamoDBRepository = Depends(get_repository),
) -> dict:
    if repo.get(expense_id) is None:
        raise HTTPException(status_code=404, detail="Not found")
    updated = Expense(id=expense_id, **expense.model_dump())
    return repo.save(updated.model_dump())


@app.delete("/expenses/{expense_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_expense(
    expense_id: str, repo: DynamoDBRepository = Depends(get_repository)
) -> Response:
    if not repo.delete(expense_id):
        raise HTTPException(status_code=404, detail="Not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", "5000")))
