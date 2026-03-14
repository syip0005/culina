"""Embedding service using pydantic-ai's Embedder with OpenRouter."""

from pydantic_ai import Embedder, EmbeddingSettings
from pydantic_ai.embeddings.openai import OpenAIEmbeddingModel
from pydantic_ai.providers.openai import OpenAIProvider

from culina_backend.service.errors import EmbeddingError


class EmbeddingService:
    def __init__(self, api_key: str, model: str, dimensions: int):
        provider = OpenAIProvider(
            base_url="https://openrouter.ai/api/v1", api_key=api_key
        )
        embedding_model = OpenAIEmbeddingModel(model, provider=provider)
        self._embedder = Embedder(
            embedding_model, settings=EmbeddingSettings(dimensions=dimensions)
        )
        self._dimensions = dimensions

    async def embed(self, text: str) -> list[float]:
        try:
            result = await self._embedder.embed_query(text)
            return list(result.embeddings[0])
        except Exception as exc:
            raise EmbeddingError(f"Failed to embed text: {exc}") from exc

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        try:
            result = await self._embedder.embed_documents(texts)
            return [list(e) for e in result.embeddings]
        except Exception as exc:
            raise EmbeddingError(f"Failed to embed batch: {exc}") from exc
