from __future__ import annotations

from google import genai

from categoryrag.config import EMBEDDING_MODEL, GEMINI_API_KEY


class EmbeddingService:
    def __init__(self) -> None:
        if not GEMINI_API_KEY:
            raise RuntimeError("GEMINI_API_KEY is not set")
        self._client = genai.Client(api_key=GEMINI_API_KEY)
        self._model = EMBEDDING_MODEL

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        vectors: list[list[float]] = []
        batch_size = 100
        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            response = self._client.models.embed_content(
                model=self._model,
                contents=batch,
            )
            for embedding in response.embeddings:
                vectors.append(list(embedding.values))
        return vectors

    def embed_query(self, query: str) -> list[float]:
        return self.embed_texts([query])[0]


_embedding_service: EmbeddingService | None = None


def get_embedding_service() -> EmbeddingService:
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService()
    return _embedding_service
