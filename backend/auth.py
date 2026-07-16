"""Authorization for the Cashlytics API.

Token validation happens before the request reaches this app: in AWS the API
Gateway Cognito JWT authorizer rejects unauthenticated requests, and locally
the API gateway proxy (local/apigw-proxy) plays the same role against
cognito-local. This module only *trusts* the claims the authorizer forwards in
the request context (surfaced by Mangum as ``request.scope["aws.event"]``) and
enforces role-based access. Requests without claims are rejected.
"""

from fastapi import HTTPException, Request, status

ADMIN_GROUP = "admin"


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
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
        )
    if ADMIN_GROUP not in groups_from_claims(claims):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Admin role required"
        )
    return claims
