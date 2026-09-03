from __future__ import annotations

from mcp.server.mcpserver import MCPServer

from categoryrag.config import ensure_data_dirs
from categoryrag.database.db import init_db

ensure_data_dirs()
init_db()

mcp = MCPServer("categoryrag")

_MCP_AUTH_MSG = {
    "error": "mcp_auth_required",
    "details": {
        "message": (
            "Dashboard auth uses httpOnly cookies; MCP API-key auth is not wired yet. "
            "Use the web dashboard for category operations for now."
        )
    },
}


@mcp.tool()
def list_categories() -> dict:
    """List all document categories available for retrieval."""
    return _MCP_AUTH_MSG


@mcp.tool()
def create_category(name: str, description: str = "") -> dict:
    """Create a new document category.

    Args:
        name: Category display name.
        description: Optional short description.
    """
    return _MCP_AUTH_MSG


@mcp.tool()
def list_documents(category_id: str) -> dict:
    """List documents in a category with indexing status.

    Args:
        category_id: Category id from list_categories.
    """
    return _MCP_AUTH_MSG


@mcp.tool()
def search_category(category_id: str, query: str, top_k: int = 5) -> dict:
    """Search a category and return relevant document chunks.

    Args:
        category_id: Category id from list_categories.
        query: Natural language question or search text.
        top_k: Maximum number of chunks to return.
    """
    return _MCP_AUTH_MSG


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
