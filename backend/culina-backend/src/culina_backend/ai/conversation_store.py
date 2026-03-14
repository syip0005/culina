from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Protocol
from uuid import UUID

from pydantic_ai.messages import ModelMessage


class ConversationStore(Protocol):
    """Storage contract for multi-turn conversation history."""

    async def get(self, conversation_id: str) -> list[ModelMessage] | None:
        """Retrieve history for a conversation, or None if not found / expired."""
        ...

    async def save(
        self, conversation_id: str, messages: list[ModelMessage], *, user_id: UUID
    ) -> None:
        """Persist the full message history for a conversation."""
        ...

    async def delete(self, conversation_id: str) -> None:
        """Remove a conversation's history."""
        ...

    async def get_user_id(self, conversation_id: str) -> UUID | None:
        """Return the owning user_id for a conversation, or None if not found."""
        ...

    async def count_by_user(self, user_id: UUID) -> int:
        """Count active (non-expired) conversations for a user."""
        ...


@dataclass
class _ConversationEntry:
    user_id: UUID
    messages: list[ModelMessage]
    last_accessed: float = field(default_factory=time.monotonic)


class InMemoryConversationStore:
    """Dict-based store with TTL and user scoping. Sufficient for single-process dev."""

    _SWEEP_INTERVAL: int = 50  # sweep expired entries every N save() calls

    def __init__(self, ttl_seconds: float = 900) -> None:
        self._store: dict[str, _ConversationEntry] = {}
        self._ttl = ttl_seconds
        self._save_count = 0

    async def get(self, conversation_id: str) -> list[ModelMessage] | None:
        entry = self._store.get(conversation_id)
        if entry is None:
            return None
        if self._is_expired(entry):
            del self._store[conversation_id]
            return None
        entry.last_accessed = time.monotonic()
        return entry.messages

    async def save(
        self, conversation_id: str, messages: list[ModelMessage], *, user_id: UUID
    ) -> None:
        self._store[conversation_id] = _ConversationEntry(
            user_id=user_id,
            messages=messages,
        )
        self._save_count += 1
        if self._save_count % self._SWEEP_INTERVAL == 0:
            self._sweep()

    async def delete(self, conversation_id: str) -> None:
        self._store.pop(conversation_id, None)

    async def get_user_id(self, conversation_id: str) -> UUID | None:
        entry = self._store.get(conversation_id)
        if entry is None or self._is_expired(entry):
            return None
        return entry.user_id

    async def count_by_user(self, user_id: UUID) -> int:
        now = time.monotonic()
        return sum(
            1
            for e in self._store.values()
            if e.user_id == user_id and (now - e.last_accessed) < self._ttl
        )

    def _is_expired(self, entry: _ConversationEntry) -> bool:
        return (time.monotonic() - entry.last_accessed) >= self._ttl

    def _sweep(self) -> None:
        expired = [cid for cid, entry in self._store.items() if self._is_expired(entry)]
        for cid in expired:
            del self._store[cid]
