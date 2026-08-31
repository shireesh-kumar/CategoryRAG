from flask import Blueprint, redirect, render_template, url_for

bp = Blueprint("dashboard", __name__)


@bp.get("/")
def home():
    return redirect(url_for("dashboard.get_dashboard"))


@bp.get("/dashboard")
def get_dashboard():
    return render_template("dashboard.html")
