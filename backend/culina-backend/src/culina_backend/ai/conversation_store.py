from __future__ import annotations

from typing import Protocol

from pydantic_ai.messages import ModelMessage


class ConversationStore(Protocol):
    """Storage contract for multi-turn conversation history."""

    async def get(self, conversation_id: str) -> list[ModelMessage] | None:
        """Retrieve history for a conversation, or None if not found."""
        ...

    async def save(self, conversation_id: str, messages: list[ModelMessage]) -> None:
        """Persist the full message history for a conversation."""
        ...

    async def delete(self, conversation_id: str) -> None:
        """Remove a conversation's history."""
        ...


class InMemoryConversationStore:
    """Dict-based store. Sufficient for single-process dev."""

    def __init__(self) -> None:
        self._store: dict[str, list[ModelMessage]] = {}

    async def get(self, conversation_id: str) -> list[ModelMessage] | None:
        return self._store.get(conversation_id)

    async def save(self, conversation_id: str, messages: list[ModelMessage]) -> None:
        self._store[conversation_id] = messages

    async def delete(self, conversation_id: str) -> None:
        self._store.pop(conversation_id, None)
