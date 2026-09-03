from __future__ import annotations

from flask import Blueprint, redirect, request, url_for

from categoryrag.config import AUTH_STATE_COOKIE
from categoryrag.exceptions import UnauthorizedError
from categoryrag.services.auth_service import (
    authorize_url,
    clear_auth_cookie,
    clear_state_cookie,
    exchange_code_for_tokens,
    get_or_create_user,
    logout_url,
    set_auth_cookie,
    set_state_cookie,
    verify_id_token,
)

bp = Blueprint("auth", __name__)


@bp.get("/login")
def login():
    url, state = authorize_url(screen_hint="login")
    response = redirect(url)
    set_state_cookie(response, state)
    return response


@bp.get("/register")
def register():
    url, state = authorize_url(screen_hint="signup")
    response = redirect(url)
    set_state_cookie(response, state)
    return response


@bp.get("/callback")
def callback():
    error = request.args.get("error")
    if error:
        response = redirect(url_for("dashboard.login_page"))
        clear_state_cookie(response)
        return response

    code = request.args.get("code")
    state = request.args.get("state")
    expected = request.cookies.get(AUTH_STATE_COOKIE)
    if not code or not state or not expected or state != expected:
        response = redirect(url_for("dashboard.login_page"))
        clear_state_cookie(response)
        clear_auth_cookie(response)
        return response

    try:
        tokens = exchange_code_for_tokens(code)
        id_token = tokens.get("id_token")
        if not id_token:
            raise UnauthorizedError(
                "auth_failed",
                {"message": "No id_token returned"},
            )
        claims = verify_id_token(id_token)
        get_or_create_user(claims)
    except UnauthorizedError:
        response = redirect(url_for("dashboard.login_page"))
        clear_state_cookie(response)
        clear_auth_cookie(response)
        return response

    response = redirect(url_for("dashboard.get_dashboard"))
    clear_state_cookie(response)
    set_auth_cookie(response, id_token)
    return response


@bp.get("/logout")
def logout():
    response = redirect(logout_url())
    clear_auth_cookie(response)
    clear_state_cookie(response)
    return response
