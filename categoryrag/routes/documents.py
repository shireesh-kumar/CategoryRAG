from flask import Blueprint, jsonify, request

from categoryrag.services.document_service import document_service

bp = Blueprint("documents", __name__)


@bp.get("/categories/<category_id>/documents")
def list_documents(category_id: str):
    docs = document_service.list(category_id)
    return jsonify([d.to_dict() for d in docs])


@bp.post("/categories/<category_id>/documents")
def upload_document(category_id: str):
    documents = document_service.upload_many(
        category_id,
        request.files.getlist("file"),
    )
    return jsonify([d.to_dict() for d in documents]), 202


@bp.delete("/categories/<category_id>/documents/<document_id>")
def delete_document(category_id: str, document_id: str):
    document_service.delete(category_id, document_id)
    return "", 204
