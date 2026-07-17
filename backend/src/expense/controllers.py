"""HTTP routes for the expense domain.

Controllers stay thin: parse the request, call the service, translate domain
exceptions into HTTP errors.
"""

from fastapi import APIRouter, Depends, HTTPException, Response, status

from src.auth.services import require_admin
from src.expense.exceptions import (
    ExpenseNotFoundError,
    InvalidMonthError,
    NonRecurringExpenseMonthError,
)
from src.expense.models import ExpenseIn, PaidStatusIn
from src.expense.services import ExpenseService, get_service

router = APIRouter(
    prefix="/expenses", tags=["expenses"], dependencies=[Depends(require_admin)]
)

_INVALID_MONTH_DETAIL = "month must be a 'YYYY-MM' string"


@router.get("")
def get_expenses(
    month: str | None = None,
    service: ExpenseService = Depends(get_service),
) -> list[dict]:
    """List expenses, optionally scoped to a single ``month`` (``YYYY-MM``).

    Omitting ``month`` preserves the old unfiltered behavior; see
    :meth:`ExpenseService.list` for the month-scoping semantics.
    """
    try:
        return service.list(month)
    except InvalidMonthError:
        raise HTTPException(status_code=400, detail=_INVALID_MONTH_DETAIL)


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


@router.put("/{expense_id}/paid")
def set_expense_paid(
    expense_id: str,
    month: str,
    body: PaidStatusIn,
    service: ExpenseService = Depends(get_service),
) -> dict:
    """Mark a specific month's instance of an expense paid/due.

    See :meth:`ExpenseService.set_paid` for the home-month-vs-other-month
    storage semantics.
    """
    try:
        return service.set_paid(expense_id, month, body.paid)
    except InvalidMonthError:
        raise HTTPException(status_code=400, detail=_INVALID_MONTH_DETAIL)
    except ExpenseNotFoundError:
        raise HTTPException(status_code=404, detail="Not found")
    except NonRecurringExpenseMonthError:
        raise HTTPException(
            status_code=400,
            detail=(
                "Only recurring expenses can be marked paid/due for a month "
                "other than their own deadline's month."
            ),
        )


@router.delete("/{expense_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_expense(
    expense_id: str, service: ExpenseService = Depends(get_service)
) -> Response:
    try:
        service.delete(expense_id)
    except ExpenseNotFoundError:
        raise HTTPException(status_code=404, detail="Not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
