from flask import Blueprint

from categoryrag.routes import categories, documents

api_bp = Blueprint("api", __name__)
api_bp.register_blueprint(categories.bp)
api_bp.register_blueprint(documents.bp)
