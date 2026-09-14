from __future__ import annotations

from mcp.server.auth.middleware.auth_context import get_access_token

from categoryrag.exceptions import AppError, UnauthorizedError
from categoryrag.models import User
from categoryrag.services.auth_service import get_or_create_user


def require_mcp_user() -> User:
    """
    Resolve the authenticated MCP caller from Cursor's Bearer token.

    After mcp_auth, Cursor stores the token and sends Authorization: Bearer …
    on each HTTP MCP request. Our OAuth AS embeds Auth0 `sub` (and profile)
    in the access token claims.
    """
    access = get_access_token()
    if access is None:
        raise UnauthorizedError(
            "mcp_auth_required",
            {
                "message": (
                    "Authenticate this MCP server in Cursor (mcp_auth / Needs login). "
                    "Sign in with Auth0 in the browser; Cursor stores the token."
                )
            },
        )

    claims = dict(access.claims or {})
    sub = access.subject or claims.get("sub")
    if not sub:
        raise UnauthorizedError(
            "invalid_token",
            {"message": "Access token missing subject"},
        )
    claims["sub"] = sub
    if "email" not in claims and access.claims:
        claims.setdefault("email", access.claims.get("email"))
    if "name" not in claims and access.claims:
        claims.setdefault("name", access.claims.get("name"))
    return get_or_create_user(claims)


def mcp_error(exc: Exception) -> dict:
    if isinstance(exc, UnauthorizedError):
        return {"error": exc.error, "details": exc.details}
    if isinstance(exc, AppError):
        return {"error": exc.error, "details": exc.details}
    return {"error": "internal_error", "details": {"message": str(exc)}}
