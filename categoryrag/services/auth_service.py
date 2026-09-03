from __future__ import annotations

import secrets
from functools import wraps
from typing import Any
from urllib.parse import urlencode

import jwt
import requests
from flask import g, jsonify, redirect, request, url_for
from jwt import PyJWKClient
from sqlalchemy import select
from werkzeug.wrappers import Response

from categoryrag.config import (
    APP_BASE_URL,
    AUTH0_CLIENT_ID,
    AUTH0_CLIENT_SECRET,
    AUTH0_DOMAIN,
    AUTH_COOKIE_MAX_AGE,
    AUTH_COOKIE_NAME,
    AUTH_STATE_COOKIE,
    IS_PRODUCTION,
)
from categoryrag.database.db import get_session
from categoryrag.exceptions import UnauthorizedError
from categoryrag.models import User, new_id, utc_now

_jwks_client: PyJWKClient | None = None


def _require_auth0_config() -> None:
    if not AUTH0_DOMAIN or not AUTH0_CLIENT_ID or not AUTH0_CLIENT_SECRET:
        raise RuntimeError(
            "AUTH0_DOMAIN, AUTH0_CLIENT_ID, and AUTH0_CLIENT_SECRET must be set"
        )


def callback_url() -> str:
    return f"{APP_BASE_URL}/callback"


def authorize_url(*, screen_hint: str | None = None) -> tuple[str, str]:
    """Build Auth0 /authorize URL and a random OAuth state value."""
    _require_auth0_config()
    state = secrets.token_urlsafe(32)
    params: dict[str, str] = {
        "response_type": "code",
        "client_id": AUTH0_CLIENT_ID,
        "redirect_uri": callback_url(),
        "scope": "openid profile email",
        "state": state,
    }
    if screen_hint:
        params["screen_hint"] = screen_hint
    url = f"https://{AUTH0_DOMAIN}/authorize?{urlencode(params)}"
    return url, state


def logout_url() -> str:
    _require_auth0_config()
    params = {
        "client_id": AUTH0_CLIENT_ID,
        "returnTo": f"{APP_BASE_URL}/login-page",
    }
    return f"https://{AUTH0_DOMAIN}/v2/logout?{urlencode(params)}"


def exchange_code_for_tokens(code: str) -> dict[str, Any]:
    _require_auth0_config()
    response = requests.post(
        f"https://{AUTH0_DOMAIN}/oauth/token",
        json={
            "grant_type": "authorization_code",
            "client_id": AUTH0_CLIENT_ID,
            "client_secret": AUTH0_CLIENT_SECRET,
            "code": code,
            "redirect_uri": callback_url(),
        },
        timeout=30,
    )
    if not response.ok:
        raise UnauthorizedError(
            "auth_failed",
            {"message": "Failed to exchange authorization code"},
        )
    return response.json()


def _jwks() -> PyJWKClient:
    global _jwks_client
    if _jwks_client is None:
        _require_auth0_config()
        _jwks_client = PyJWKClient(f"https://{AUTH0_DOMAIN}/.well-known/jwks.json")
    return _jwks_client


def verify_id_token(id_token: str) -> dict[str, Any]:
    """Verify Auth0-signed ID token (JWT) and return claims."""
    _require_auth0_config()
    try:
        signing_key = _jwks().get_signing_key_from_jwt(id_token)
        return jwt.decode(
            id_token,
            signing_key.key,
            algorithms=["RS256"],
            audience=AUTH0_CLIENT_ID,
            issuer=f"https://{AUTH0_DOMAIN}/",
        )
    except jwt.PyJWTError as exc:
        raise UnauthorizedError(
            "invalid_token",
            {"message": "Invalid or expired identity token"},
        ) from exc


def get_or_create_user(claims: dict[str, Any]) -> User:
    sub = claims.get("sub")
    if not sub:
        raise UnauthorizedError(
            "invalid_token",
            {"message": "Token missing subject"},
        )
    email = claims.get("email")
    name = claims.get("name") or claims.get("nickname")
    now = utc_now()

    with get_session() as session:
        user = session.scalars(select(User).where(User.auth0_sub == sub)).first()
        if user:
            changed = False
            if email and user.email != email:
                user.email = email
                changed = True
            if name and user.name != name:
                user.name = name
                changed = True
            if changed:
                user.updated_at = now
                session.commit()
                session.refresh(user)
            return user

        user = User(
            id=new_id(),
            auth0_sub=sub,
            email=email,
            name=name,
            created_at=now,
            updated_at=now,
        )
        session.add(user)
        session.commit()
        session.refresh(user)
        return user


def set_auth_cookie(response: Response, id_token: str) -> None:
    """httpOnly JWT cookie. SameSite=Strict for app traffic after login."""
    response.set_cookie(
        AUTH_COOKIE_NAME,
        id_token,
        max_age=AUTH_COOKIE_MAX_AGE,
        httponly=True,
        secure=IS_PRODUCTION,
        samesite="Strict",
        path="/",
    )


def clear_auth_cookie(response: Response) -> None:
    response.delete_cookie(
        AUTH_COOKIE_NAME,
        path="/",
        samesite="Strict",
        secure=IS_PRODUCTION,
    )


def set_state_cookie(response: Response, state: str) -> None:
    """
    OAuth state cookie must be SameSite=Lax so Auth0's redirect back
    to /callback still includes it (cross-site top-level GET).
    """
    response.set_cookie(
        AUTH_STATE_COOKIE,
        state,
        max_age=600,
        httponly=True,
        secure=IS_PRODUCTION,
        samesite="Lax",
        path="/",
    )


def clear_state_cookie(response: Response) -> None:
    response.delete_cookie(
        AUTH_STATE_COOKIE,
        path="/",
        samesite="Lax",
        secure=IS_PRODUCTION,
    )


def current_user_from_cookie() -> User | None:
    token = request.cookies.get(AUTH_COOKIE_NAME)
    if not token:
        return None
    claims = verify_id_token(token)
    with get_session() as session:
        user = session.scalars(
            select(User).where(User.auth0_sub == claims["sub"])
        ).first()
        return user


def login_required(view):
    """Protect HTML pages — redirect to /login when unauthenticated."""

    @wraps(view)
    def wrapped(*args, **kwargs):
        try:
            user = current_user_from_cookie()
        except UnauthorizedError:
            clear = redirect(url_for("dashboard.login_page"))
            clear_auth_cookie(clear)
            return clear
        if not user:
            return redirect(url_for("dashboard.login_page"))
        g.current_user = user
        return view(*args, **kwargs)

    return wrapped


def api_login_required(view):
    """Protect JSON API — 401 when unauthenticated."""

    @wraps(view)
    def wrapped(*args, **kwargs):
        try:
            user = current_user_from_cookie()
        except UnauthorizedError as exc:
            return jsonify({"error": exc.error, "details": exc.details}), 401
        if not user:
            return jsonify(
                {"error": "unauthorized", "details": {"message": "Login required"}}
            ), 401
        g.current_user = user
        return view(*args, **kwargs)

    return wrapped
