from flask import Blueprint
from flask import render_template


bp = Blueprint("dashboard",__name__)

@bp.get("/dashboard")
def get_dashboard():
    return render_template("dashboard.html")

    

