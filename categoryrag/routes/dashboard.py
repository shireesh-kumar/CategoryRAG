from flask import Blueprint, redirect, render_template, url_for

from categoryrag.services.auth_service import login_required

bp = Blueprint("dashboard", __name__)


@bp.get("/")
def home():
    return redirect(url_for("dashboard.get_dashboard"))


@bp.get("/dashboard")
@login_required
def get_dashboard():
    return render_template("dashboard.html")


@bp.get("/login-page")
def login_page():
    return render_template("login.html")


@bp.get("/register-page")
def register_page():
    return render_template("register.html")
