"""Authorization for the Cashlytics API.

Token validation happens at the edge: API Gateway's Cognito JWT authorizer
rejects unauthenticated requests before they reach the Lambda. This module only
*trusts* the claims the authorizer forwards in the request context (surfaced by
Mangum as ``request.scope["aws.event"]``) and enforces role-based access.

Local development and the test suite run without API Gateway; setting
``AUTH_BYPASS=true`` short-circuits the dependency with fake admin claims.
Never set it in AWS.
"""

import os

from fastapi import HTTPException, Request, status

ADMIN_GROUP = "admin"


def _bypass_enabled() -> bool:
    return os.environ.get("AUTH_BYPASS", "").lower() == "true"


def _extract_claims(request: Request) -> dict | None:
    event = request.scope.get("aws.event") or {}
    authorizer = (event.get("requestContext") or {}).get("authorizer") or {}
    return (authorizer.get("jwt") or {}).get("claims")


def groups_from_claims(claims: dict) -> list[str]:
    """Cognito groups from JWT claims.

    The HTTP API JWT authorizer serialises the ``cognito:groups`` list as a
    string like ``"[admin other]"``; raw tokens carry a real list. Handle both.
    """
    raw = claims.get("cognito:groups") or []
    if isinstance(raw, str):
        raw = raw.strip("[]").replace(",", " ").split()
    return [str(group).strip() for group in raw if str(group).strip()]


def require_admin(request: Request) -> dict:
    """FastAPI dependency: the caller must belong to the ``admin`` group."""
    claims = _extract_claims(request)
    if claims is None:
        if _bypass_enabled():
            return {"email": "local@cashlytics.dev", "cognito:groups": [ADMIN_GROUP]}
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
        )
    if ADMIN_GROUP not in groups_from_claims(claims):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Admin role required"
        )
    return claims
