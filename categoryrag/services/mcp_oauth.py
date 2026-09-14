"""Auth0-backed OAuth authorization server for HTTP MCP (Cursor mcp_auth).

Cursor talks to this MCP server as the OAuth AS (DCR + authorize/token).
We proxy the human login to Auth0 using the existing Regular Web App credentials,
then issue MCP access tokens Cursor stores and sends as Bearer.

Access/refresh tokens are stored in Postgres (mcp_access_tokens / mcp_refresh_tokens)
so they survive MCP restarts and work across instances. Short-lived OAuth handshake
state (pending login, auth codes, DCR clients) stays in memory.
"""

from __future__ import annotations

import secrets
import time
from dataclasses import dataclass
from typing import Any

from starlette.requests import Request
from starlette.responses import HTMLResponse, RedirectResponse, Response

from mcp.server.auth.provider import (
    AccessToken,
    AuthorizationCode,
    AuthorizationParams,
    RefreshToken,
    TokenError,
    construct_redirect_uri,
)
from mcp.shared.auth import OAuthClientInformationFull, OAuthToken

from categoryrag.config import MCP_AUTH0_CALLBACK_URL
from categoryrag.database.db import get_session
from categoryrag.exceptions import UnauthorizedError
from categoryrag.models import McpAccessToken, McpRefreshToken
from categoryrag.services.auth_service import (
    authorize_url,
    exchange_code_for_tokens,
    get_or_create_user,
    verify_id_token,
)

_CODE_TTL_SECONDS = 300
_ACCESS_TTL_SECONDS = 60 * 60
_REFRESH_TTL_SECONDS = 60 * 60 * 24 * 30


@dataclass
class _PendingAuth:
    client_id: str
    params: AuthorizationParams
    auth0_state: str


class Auth0McpOAuthProvider:
    """OAuth AS that proxies interactive login to Auth0; sessions live in the DB."""

    def __init__(self) -> None:
        self._clients: dict[str, OAuthClientInformationFull] = {}
        self._pending: dict[str, _PendingAuth] = {}
        self._auth_codes: dict[str, AuthorizationCode] = {}
        self._code_claims: dict[str, dict[str, Any]] = {}

    async def get_client(self, client_id: str) -> OAuthClientInformationFull | None:
        return self._clients.get(client_id)

    async def register_client(self, client_info: OAuthClientInformationFull) -> None:
        self._clients[client_info.client_id] = client_info

    async def authorize(
        self, client: OAuthClientInformationFull, params: AuthorizationParams
    ) -> str:
        auth0_state = secrets.token_urlsafe(32)
        self._pending[auth0_state] = _PendingAuth(
            client_id=client.client_id,
            params=params,
            auth0_state=auth0_state,
        )
        url, _ = authorize_url(
            redirect_uri=MCP_AUTH0_CALLBACK_URL,
            state=auth0_state,
        )
        return url

    async def handle_auth0_callback(self, request: Request) -> Response:
        error = request.query_params.get("error")
        if error:
            desc = request.query_params.get("error_description") or error
            return HTMLResponse(
                f"<h1>Auth failed</h1><p>{desc}</p>",
                status_code=400,
            )

        code = request.query_params.get("code")
        state = request.query_params.get("state")
        if not code or not state:
            return HTMLResponse("<h1>Missing code or state</h1>", status_code=400)

        pending = self._pending.pop(state, None)
        if pending is None:
            return HTMLResponse("<h1>Invalid or expired state</h1>", status_code=400)

        client = self._clients.get(pending.client_id)
        if client is None:
            return HTMLResponse("<h1>Unknown client</h1>", status_code=400)

        try:
            tokens = exchange_code_for_tokens(
                code, redirect_uri=MCP_AUTH0_CALLBACK_URL
            )
            id_token = tokens.get("id_token")
            if not id_token:
                raise UnauthorizedError(
                    "auth_failed",
                    {"message": "Auth0 did not return an id_token"},
                )
            claims = verify_id_token(id_token)
            get_or_create_user(claims)
        except UnauthorizedError as exc:
            return HTMLResponse(
                f"<h1>Auth failed</h1><p>{exc.details.get('message', exc.error)}</p>",
                status_code=400,
            )

        mcp_code = secrets.token_urlsafe(32)
        now = time.time()
        scopes = pending.params.scopes or ["openid", "profile", "email"]
        auth_code = AuthorizationCode(
            code=mcp_code,
            scopes=scopes,
            expires_at=now + _CODE_TTL_SECONDS,
            client_id=pending.client_id,
            code_challenge=pending.params.code_challenge,
            redirect_uri=pending.params.redirect_uri,
            redirect_uri_provided_explicitly=pending.params.redirect_uri_provided_explicitly,
            resource=pending.params.resource,
            subject=claims.get("sub"),
        )
        self._auth_codes[mcp_code] = auth_code
        self._code_claims[mcp_code] = claims

        redirect = construct_redirect_uri(
            str(pending.params.redirect_uri),
            code=mcp_code,
            state=pending.params.state,
        )
        return RedirectResponse(url=redirect, status_code=302)

    async def load_authorization_code(
        self, client: OAuthClientInformationFull, authorization_code: str
    ) -> AuthorizationCode | None:
        code = self._auth_codes.get(authorization_code)
        if not code:
            return None
        if code.client_id != client.client_id:
            return None
        if code.expires_at < time.time():
            self._auth_codes.pop(authorization_code, None)
            self._code_claims.pop(authorization_code, None)
            return None
        return code

    async def exchange_authorization_code(
        self, client: OAuthClientInformationFull, authorization_code: AuthorizationCode
    ) -> OAuthToken:
        stored = self._auth_codes.pop(authorization_code.code, None)
        claims = self._code_claims.pop(authorization_code.code, None) or {}
        if stored is None:
            raise TokenError(
                error="invalid_grant",
                error_description="Authorization code not found",
            )

        return self._mint_tokens(
            client_id=client.client_id,
            scopes=stored.scopes,
            subject=stored.subject,
            resource=stored.resource,
            claims=claims,
        )

    async def load_refresh_token(
        self, client: OAuthClientInformationFull, refresh_token: str
    ) -> RefreshToken | None:
        with get_session() as session:
            row = session.get(McpRefreshToken, refresh_token)
            if row is None or row.client_id != client.client_id:
                return None
            if row.expires_at < int(time.time()):
                session.delete(row)
                session.commit()
                return None
            return RefreshToken(
                token=row.token,
                client_id=row.client_id,
                scopes=row.scopes.split(),
                expires_at=row.expires_at,
                subject=row.subject,
            )

    async def exchange_refresh_token(
        self,
        client: OAuthClientInformationFull,
        refresh_token: RefreshToken,
        scopes: list[str],
    ) -> OAuthToken:
        with get_session() as session:
            row = session.get(McpRefreshToken, refresh_token.token)
            if row is None or row.client_id != client.client_id:
                raise TokenError(
                    error="invalid_grant",
                    error_description="Refresh token not found",
                )
            if row.expires_at < int(time.time()):
                session.delete(row)
                session.commit()
                raise TokenError(
                    error="invalid_grant",
                    error_description="Refresh token expired",
                )
            claims = {
                "sub": row.subject,
                "email": row.email,
                "name": row.name,
            }
            subject = row.subject
            granted = scopes or row.scopes.split()
            session.delete(row)
            session.commit()

        return self._mint_tokens(
            client_id=client.client_id,
            scopes=granted,
            subject=subject,
            resource=None,
            claims=claims,
        )

    async def load_access_token(self, token: str) -> AccessToken | None:
        with get_session() as session:
            row = session.get(McpAccessToken, token)
            if row is None:
                return None
            if row.expires_at < int(time.time()):
                session.delete(row)
                session.commit()
                return None
            return AccessToken(
                token=row.token,
                client_id=row.client_id,
                scopes=row.scopes.split(),
                expires_at=row.expires_at,
                resource=row.resource,
                subject=row.subject,
                claims={
                    "sub": row.subject,
                    "email": row.email,
                    "name": row.name,
                },
            )

    async def revoke_token(self, token: AccessToken | RefreshToken) -> None:
        with get_session() as session:
            if isinstance(token, AccessToken):
                row = session.get(McpAccessToken, token.token)
            else:
                row = session.get(McpRefreshToken, token.token)
            if row is not None:
                session.delete(row)
                session.commit()

    def _mint_tokens(
        self,
        *,
        client_id: str,
        scopes: list[str],
        subject: str | None,
        resource: str | None,
        claims: dict[str, Any],
    ) -> OAuthToken:
        if not subject:
            raise TokenError(
                error="invalid_grant",
                error_description="Missing subject",
            )
        user = get_or_create_user(
            {
                "sub": subject,
                "email": claims.get("email"),
                "name": claims.get("name") or claims.get("nickname"),
            }
        )
        now = int(time.time())
        access = secrets.token_urlsafe(32)
        refresh = secrets.token_urlsafe(32)
        email = claims.get("email")
        name = claims.get("name") or claims.get("nickname")
        scope_str = " ".join(scopes)

        with get_session() as session:
            session.add(
                McpAccessToken(
                    token=access,
                    user_id=user.id,
                    client_id=client_id,
                    scopes=scope_str,
                    subject=subject,
                    email=email,
                    name=name,
                    resource=resource,
                    expires_at=now + _ACCESS_TTL_SECONDS,
                )
            )
            session.add(
                McpRefreshToken(
                    token=refresh,
                    user_id=user.id,
                    client_id=client_id,
                    scopes=scope_str,
                    subject=subject,
                    email=email,
                    name=name,
                    expires_at=now + _REFRESH_TTL_SECONDS,
                )
            )
            session.commit()

        return OAuthToken(
            access_token=access,
            token_type="Bearer",
            expires_in=_ACCESS_TTL_SECONDS,
            scope=scope_str,
            refresh_token=refresh,
        )
