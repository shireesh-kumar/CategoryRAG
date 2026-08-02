from flask import Blueprint, jsonify, request

from categoryrag.services.category_service import category_service
from categoryrag.services.document_service import document_service
from categoryrag.services.retriever_registry import retriever_registry

bp = Blueprint("categories", __name__)


@bp.get("/categories")
def list_categories():
    categories = [c.to_dict() for c in category_service.list()]
    return jsonify(categories)


@bp.post("/categories")
def create_category():
    payload = request.get_json(silent=True) or {}
    name = payload.get("name", "")
    description = payload.get("description", "")
    try:
        category = category_service.create(name=name, description=description)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify(category.to_dict()), 201


@bp.get("/categories/<category_id>")
def get_category(category_id: str):
    category = category_service.get(category_id)
    if not category:
        return jsonify({"error": "Category not found"}), 404
    docs = [d.to_dict() for d in document_service.list(category_id)]
    return jsonify({"category": category.to_dict(), "documents": docs})


@bp.delete("/categories/<category_id>")
def delete_category(category_id: str):
    if not category_service.get(category_id):
        return jsonify({"error": "Category not found"}), 404
    document_service.delete_category_files(category_id)
    retriever_registry.delete_category(category_id)
    category_service.delete(category_id)
    return "", 204
