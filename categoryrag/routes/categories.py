from flask import Blueprint, g, jsonify, request

from categoryrag.services.auth_service import api_login_required
from categoryrag.services.category_service import category_service

bp = Blueprint("categories", __name__)


@bp.get("/categories")
@api_login_required
def list_categories():
    return jsonify([c.to_dict() for c in category_service.list(g.current_user.id)])


@bp.post("/categories")
@api_login_required
def create_category():
    payload = request.get_json(silent=True) or {}
    category = category_service.create(
        user_id=g.current_user.id,
        name=payload.get("name", ""),
        description=payload.get("description", ""),
    )
    return jsonify(category.to_dict()), 201


@bp.get("/categories/<category_id>")
@api_login_required
def get_category(category_id: str):
    return jsonify(category_service.get_detail(category_id, user_id=g.current_user.id))


@bp.post("/categories/<category_id>/search")
@api_login_required
def search_category(category_id: str):
    payload = request.get_json(silent=True) or {}
    results = category_service.search(
        category_id,
        user_id=g.current_user.id,
        query=payload.get("query", ""),
        top_k=payload.get("top_k", 5),
    )
    return jsonify(results)


@bp.delete("/categories/<category_id>")
@api_login_required
def delete_category(category_id: str):
    category_service.delete(category_id, user_id=g.current_user.id)
    return "", 204
