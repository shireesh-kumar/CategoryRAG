from __future__ import annotations

import logging
import uuid
from pathlib import Path

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PointStruct,
    VectorParams,
)

from categoryrag.config import EMBEDDING_DIM, QDRANT_API_KEY, QDRANT_URL
from categoryrag.services.chunking import chunk_text
from categoryrag.services.embeddings import get_embedding_service
from categoryrag.services.text_extractor import extract_text

logger = logging.getLogger(__name__)


class RetrieverRegistry:
    def __init__(self) -> None:
        if not QDRANT_URL:
            raise RuntimeError("QDRANT_URL must be set")
        self._client = QdrantClient(
            url=QDRANT_URL,
            api_key=QDRANT_API_KEY or None,
        )

    def ensure_category(self, category_id: str) -> None:
        if self._client.collection_exists(category_id):
            return
        self._client.create_collection(
            collection_name=category_id,
            vectors_config=VectorParams(size=EMBEDDING_DIM, distance=Distance.COSINE),
        )

    def ingest_document(
        self,
        *,
        category_id: str,
        document_id: str,
        filename: str,
        stored_name: str,
        file_path: Path,
    ) -> int:
        self.ensure_category(category_id)
        text = extract_text(file_path)
        chunks = chunk_text(text)
        if not chunks:
            logger.warning("No text chunks for document %s", document_id)
            return 0

        vectors = get_embedding_service().embed_texts(chunks)
        points = [
            PointStruct(
                id=str(uuid.uuid4()),
                vector=vector,
                payload={
                    "category_id": category_id,
                    "document_id": document_id,
                    "filename": filename,
                    "stored_name": stored_name,
                    "chunk_index": index,
                    "text": chunk,
                },
            )
            for index, (chunk, vector) in enumerate(zip(chunks, vectors))
        ]
        self._client.upsert(collection_name=category_id, points=points)
        return len(points)

    def delete_document(self, category_id: str, document_id: str) -> None:
        if not self._client.collection_exists(category_id):
            return
        self._client.delete(
            collection_name=category_id,
            points_selector=Filter(
                must=[
                    FieldCondition(
                        key="document_id",
                        match=MatchValue(value=document_id),
                    )
                ]
            ),
        )

    def delete_category(self, category_id: str) -> None:
        if not self._client.collection_exists(category_id):
            return
        self._client.delete_collection(collection_name=category_id)

    def search(self, category_id: str, query: str, top_k: int = 5) -> list[dict]:
        if not self._client.collection_exists(category_id):
            return []
        vector = get_embedding_service().embed_query(query)
        results = self._client.query_points(
            collection_name=category_id,
            query=vector,
            limit=top_k,
            with_payload=True,
        )
        return [
            {
                "score": point.score,
                "document_id": (point.payload or {}).get("document_id"),
                "filename": (point.payload or {}).get("filename"),
                "chunk_index": (point.payload or {}).get("chunk_index"),
                "text": (point.payload or {}).get("text"),
            }
            for point in results.points
        ]


retriever_registry = RetrieverRegistry()
