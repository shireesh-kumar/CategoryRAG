from __future__ import annotations

from mcp.server.auth.middleware.auth_context import get_access_token
from mcp.server.auth.provider import AccessToken, TokenVerifier

from categoryrag.config import AUTH0_MCP_AUDIENCE, MCP_RESOURCE_URL
from categoryrag.exceptions import AppError, UnauthorizedError
from categoryrag.models import User
from categoryrag.services.auth_service import get_or_create_user, verify_access_token


class Auth0TokenVerifier(TokenVerifier):
    """Accept Auth0 access tokens whose audience is this MCP server."""

    async def verify_token(self, token: str) -> AccessToken | None:
        try:
            claims = verify_access_token(token, audience=AUTH0_MCP_AUDIENCE)
        except UnauthorizedError:
            return None

        sub = claims.get("sub")
        if not sub:
            return None

        scope = claims.get("scope") or ""
        scopes = scope.split() if isinstance(scope, str) else list(scope)
        exp = claims.get("exp")
        client_id = claims.get("azp") or claims.get("client_id") or ""

        return AccessToken(
            token=token,
            client_id=str(client_id),
            scopes=scopes,
            expires_at=int(exp) if exp is not None else None,
            resource=MCP_RESOURCE_URL,
            subject=str(sub),
            claims=claims,
        )


def require_mcp_user() -> User:
    """Resolve the caller from the Auth0 access token on this request."""
    access = get_access_token()
    if access is None:
        raise UnauthorizedError(
            "mcp_auth_required",
            {
                "message": (
                    "Sign in with Auth0 for this MCP server. "
                    "The client stores the access token and sends it as Bearer."
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
    return get_or_create_user(claims)


def mcp_error(exc: Exception) -> dict:
    if isinstance(exc, UnauthorizedError):
        return {"error": exc.error, "details": exc.details}
    if isinstance(exc, AppError):
        return {"error": exc.error, "details": exc.details}
    return {"error": "internal_error", "details": {"message": str(exc)}}
