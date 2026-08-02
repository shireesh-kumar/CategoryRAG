from flask import Blueprint, jsonify, request

from categoryrag.services.document_service import document_service
from categoryrag.services.ingest import ingest_worker
from categoryrag.services.retriever_registry import retriever_registry

bp = Blueprint("documents", __name__)


@bp.get("/categories/<category_id>/documents")
def list_documents(category_id: str):
    try:
        docs = document_service.list(category_id)
    except KeyError as exc:
        return jsonify({"error": str(exc)}), 404
    return jsonify([d.to_dict() for d in docs])


@bp.post("/categories/<category_id>/documents")
def upload_document(category_id: str):
    if "file" not in request.files:
        return jsonify({"error": "Expected multipart form field 'file'"}), 400
    try:
        document = document_service.upload(category_id, request.files["file"])
    except KeyError as exc:
        return jsonify({"error": str(exc)}), 404
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    ingest_worker.enqueue(document.id)
    return jsonify(document.to_dict()), 202


@bp.delete("/categories/<category_id>/documents/<document_id>")
def delete_document(category_id: str, document_id: str):
    document = document_service.get(document_id)
    if not document or document.category_id != category_id:
        return jsonify({"error": "Document not found"}), 404
    retriever_registry.delete_document(category_id, document_id)
    document_service.delete(category_id, document_id)
    return "", 204
