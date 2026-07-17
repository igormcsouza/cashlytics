"""HTTP routes for the expense domain.

Controllers stay thin: parse the request, call the service, translate domain
exceptions into HTTP errors.
"""

from fastapi import APIRouter, Depends, HTTPException, Response, status

from src.auth.services import bearer_scheme, require_admin
from src.expense.exceptions import ExpenseNotFoundError
from src.expense.models import ExpenseIn
from src.expense.services import ExpenseService, get_service

router = APIRouter(
    prefix="/expenses",
    tags=["expenses"],
    # bearer_scheme only makes Swagger UI show "Authorize" and attach the
    # token you paste there; require_admin is what actually enforces it.
    dependencies=[Depends(bearer_scheme), Depends(require_admin)],
)


@router.get("")
def get_expenses(service: ExpenseService = Depends(get_service)) -> list[dict]:
    return service.list()


@router.post("", status_code=status.HTTP_201_CREATED)
def create_expense(
    expense: ExpenseIn, service: ExpenseService = Depends(get_service)
) -> dict:
    return service.create(expense)


@router.put("/{expense_id}")
def update_expense(
    expense_id: str,
    expense: ExpenseIn,
    service: ExpenseService = Depends(get_service),
) -> dict:
    try:
        return service.update(expense_id, expense)
    except ExpenseNotFoundError:
        raise HTTPException(status_code=404, detail="Not found")


@router.delete("/{expense_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_expense(
    expense_id: str, service: ExpenseService = Depends(get_service)
) -> Response:
    try:
        service.delete(expense_id)
    except ExpenseNotFoundError:
        raise HTTPException(status_code=404, detail="Not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
