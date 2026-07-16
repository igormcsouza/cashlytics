"""Authorization for the auth domain.

Token validation happens before a request reaches this app: in AWS the API
Gateway Cognito JWT authorizer rejects unauthenticated requests, and locally
the API gateway proxy (local/apigw-proxy) plays the same role against
cognito-local. This module only *trusts* the claims the authorizer forwards in
the request context (surfaced by Mangum as ``request.scope["aws.event"]``) and
enforces role-based access. Requests without claims are rejected.

This domain intentionally doesn't have the full five-file shape other domains
do (see CLAUDE.md): there's no persisted entity, so models.py/exceptions.py/
repositories.py don't apply, and it exposes no routes of its own (controllers.py)
— it's consumed as a dependency by other domains' controllers instead (see
src/expense/controllers.py). bootstrap.py, alongside this file, is local-only
tooling that provisions cognito-local, mirroring src/core/bootstrap.py.
"""

from fastapi import HTTPException, Request, status

# Must match Config.ADMIN_GROUP in infra/stacks/config.py (the CfnUserPoolGroup
# name CDK creates). The two are in separate, independently-deployed Python
# projects with no shared package, so this can't be a single import — if you
# rename one, rename the other, or every admin silently starts 403ing.
ADMIN_GROUP = "admin"


def _extract_claims(request: Request) -> dict | None:
    event = request.scope.get("aws.event") or {}
    authorizer = (event.get("requestContext") or {}).get("authorizer") or {}
    return (authorizer.get("jwt") or {}).get("claims")


def groups_from_claims(claims: dict) -> list[str]:
    """Cognito groups from JWT claims.

    The HTTP API JWT authorizer serialises the ``cognito:groups`` list as a
    string like ``"[admin other]"``; raw tokens carry a real list. Handle both.

    This is the source of truth for the bracket format: it must decode
    whatever AWS's real authorizer actually sends. local/apigw-proxy/proxy.py's
    ``_decode_claims`` encodes claims the same way to emulate it for local dev
    — keep that encoding in sync with this decoder if either changes.
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
