from flask import Blueprint, g, jsonify, request

from categoryrag.services.auth_service import api_login_required
from categoryrag.services.document_service import document_service

bp = Blueprint("documents", __name__)


@bp.get("/categories/<category_id>/documents")
@api_login_required
def list_documents(category_id: str):
    docs = document_service.list(category_id, user_id=g.current_user.id)
    return jsonify([d.to_dict() for d in docs])


@bp.post("/categories/<category_id>/documents")
@api_login_required
def upload_document(category_id: str):
    document_service.upload_many(
        category_id,
        user_id=g.current_user.id,
        files=request.files.getlist("file"),
    )
    return jsonify({"message": "Upload accepted"}), 202


@bp.delete("/categories/<category_id>/documents/<document_id>")
@api_login_required
def delete_document(category_id: str, document_id: str):
    document_service.delete(category_id, document_id, user_id=g.current_user.id)
    return "", 204
