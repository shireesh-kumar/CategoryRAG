from flask import Blueprint, jsonify, request

from categoryrag.services.category_service import category_service

bp = Blueprint("categories", __name__)


@bp.get("/categories")
def list_categories():
    return jsonify([c.to_dict() for c in category_service.list()])


@bp.post("/categories")
def create_category():
    payload = request.get_json(silent=True) or {}
    category = category_service.create(
        name=payload.get("name", ""),
        description=payload.get("description", ""),
    )
    return jsonify(category.to_dict()), 201


@bp.get("/categories/<category_id>")
def get_category(category_id: str):
    return jsonify(category_service.get_detail(category_id))


@bp.delete("/categories/<category_id>")
def delete_category(category_id: str):
    category_service.delete(category_id)
    return "", 204
