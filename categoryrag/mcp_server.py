from __future__ import annotations

from mcp.server.mcpserver import MCPServer

from categoryrag.config import ensure_data_dirs
from categoryrag.database.db import init_db
from categoryrag.exceptions import AppError
from categoryrag.services.category_service import category_service
from categoryrag.services.document_service import document_service

ensure_data_dirs()
init_db()

mcp = MCPServer("categoryrag")


@mcp.tool()
def list_categories() -> list[dict]:
    """List all document categories available for retrieval."""
    return [c.to_dict() for c in category_service.list()]


@mcp.tool()
def create_category(name: str, description: str = "") -> dict:
    """Create a new document category.

    Args:
        name: Category display name.
        description: Optional short description.
    """
    try:
        return category_service.create(name=name, description=description).to_dict()
    except AppError as exc:
        return {"error": exc.error, "details": exc.details}


@mcp.tool()
def list_documents(category_id: str) -> list[dict] | dict:
    """List documents in a category with indexing status.

    Args:
        category_id: Category id from list_categories.
    """
    try:
        documents = document_service.list(category_id)
    except AppError as exc:
        return {"error": exc.error, "details": exc.details}
    return [
        {
            "id": document.id,
            "filename": document.filename,
            "status": document.status,
            "error": document.error,
        }
        for document in documents
    ]


@mcp.tool()
def search_category(category_id: str, query: str, top_k: int = 5) -> list[dict] | dict:
    """Search a category and return relevant document chunks.

    Args:
        category_id: Category id from list_categories.
        query: Natural language question or search text.
        top_k: Maximum number of chunks to return.
    """
    try:
        return category_service.search(category_id, query=query, top_k=top_k)
    except AppError as exc:
        return {"error": exc.error, "details": exc.details}


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
