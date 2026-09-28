from __future__ import annotations

from pydantic import AnyHttpUrl

from mcp.server.auth.settings import AuthSettings
from mcp.server.mcpserver import MCPServer

from categoryrag.config import (
    AUTH0_ISSUER,
    MCP_HOST,
    MCP_PATH,
    MCP_PORT,
    MCP_RESOURCE_URL,
    ensure_data_dirs,
)
from categoryrag.database.db import init_db
from categoryrag.exceptions import AppError, UnauthorizedError
from categoryrag.services.category_service import category_service
from categoryrag.services.document_service import document_service
from categoryrag.services.mcp_auth import Auth0TokenVerifier, mcp_error, require_mcp_user

ensure_data_dirs()
init_db()

if not AUTH0_ISSUER:
    raise RuntimeError("AUTH0_DOMAIN must be set for MCP authentication")

mcp = MCPServer(
    "categoryrag",
    token_verifier=Auth0TokenVerifier(),
    auth=AuthSettings(
        issuer_url=AnyHttpUrl(AUTH0_ISSUER),
        resource_server_url=AnyHttpUrl(MCP_RESOURCE_URL),
    ),
)


@mcp.tool()
def list_categories() -> list[dict] | dict:
    """List all document categories available for retrieval for the authenticated user."""
    try:
        user = require_mcp_user()
        return [c.to_dict() for c in category_service.list(user.id)]
    except (UnauthorizedError, AppError) as exc:
        return mcp_error(exc)


@mcp.tool()
def create_category(name: str, description: str = "") -> dict:
    """Create a new document category.

    Args:
        name: Category display name.
        description: Optional short description.
    """
    try:
        user = require_mcp_user()
        return category_service.create(
            user_id=user.id,
            name=name,
            description=description,
        ).to_dict()
    except (UnauthorizedError, AppError) as exc:
        return mcp_error(exc)


@mcp.tool()
def list_documents(category_id: str) -> list[dict] | dict:
    """List documents in a category with indexing status.

    Args:
        category_id: Category id from list_categories.
    """
    try:
        user = require_mcp_user()
        documents = document_service.list(category_id, user_id=user.id)
        return [
            {
                "id": document.id,
                "filename": document.filename,
                "status": document.status,
                "error": document.error,
            }
            for document in documents
        ]
    except (UnauthorizedError, AppError) as exc:
        return mcp_error(exc)


@mcp.tool()
def search_category(category_id: str, query: str, top_k: int = 5) -> list[dict] | dict:
    """Search a category and return relevant document chunks.

    Args:
        category_id: Category id from list_categories.
        query: Natural language question or search text.
        top_k: Maximum number of chunks to return.
    """
    try:
        user = require_mcp_user()
        return category_service.search(
            category_id,
            user_id=user.id,
            query=query,
            top_k=top_k,
        )
    except (UnauthorizedError, AppError) as exc:
        return mcp_error(exc)


def main() -> None:
    mcp.run(
        transport="streamable-http",
        host=MCP_HOST,
        port=MCP_PORT,
        streamable_http_path=MCP_PATH,
        stateless_http=True,
        json_response=True,
    )


if __name__ == "__main__":
    main()
