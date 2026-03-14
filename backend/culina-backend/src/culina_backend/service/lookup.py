"""Lookup service — orchestrates NutritionLookup with ConversationStore."""

from __future__ import annotations

import base64
from dataclasses import dataclass
from uuid import UUID, uuid4

from pydantic_ai import BinaryContent
from pydantic_ai.messages import UserContent

from culina_backend.ai.conversation_store import ConversationStore
from culina_backend.ai.model.follow_up import FollowUpQuestion
from culina_backend.ai.nutrition_lookup import NutritionLookup
from culina_backend.model import SearchNutritionResult
from culina_backend.service.errors import (
    ConversationLimitError,
    ForbiddenError,
    NotFoundError,
)


@dataclass(frozen=True, slots=True)
class LookupResult:
    """Result returned to the route layer."""

    conversation_id: str
    output: SearchNutritionResult | FollowUpQuestion


class LookupService:
    def __init__(
        self,
        nutrition_lookup: NutritionLookup,
        conversation_store: ConversationStore,
        max_conversations_per_user: int = 3,
    ) -> None:
        self._lookup = nutrition_lookup
        self._store = conversation_store
        self._max_conversations = max_conversations_per_user

    async def lookup(
        self,
        user_id: UUID,
        *,
        text: str | None = None,
        image_base64: str | None = None,
        image_media_type: str = "image/jpeg",
        conversation_id: str | None = None,
    ) -> LookupResult:
        """Run a nutrition lookup turn.

        Args:
            user_id: Authenticated user.
            text: Text query (e.g. "large big mac meal").
            image_base64: Base64-encoded image data.
            image_media_type: MIME type for the image (default image/jpeg).
            conversation_id: Existing conversation to continue, or None to start new.
        """
        # Resolve or create conversation
        if conversation_id is not None:
            owner = await self._store.get_user_id(conversation_id)
            if owner is None:
                raise NotFoundError(f"Conversation {conversation_id} not found")
            if owner != user_id:
                raise ForbiddenError("Not your conversation")
            messages = await self._store.get(conversation_id)
        else:
            count = await self._store.count_by_user(user_id)
            if count >= self._max_conversations:
                raise ConversationLimitError(
                    f"Too many active conversations (max {self._max_conversations})"
                )
            conversation_id = uuid4().hex
            messages = None

        # Build user prompt
        prompt = _build_prompt(text, image_base64, image_media_type)

        # Call AI
        response = await self._lookup.send(prompt, message_history=messages)

        # Always save — conversation stays alive until TTL expires
        await self._store.save(conversation_id, response.messages, user_id=user_id)

        return LookupResult(conversation_id=conversation_id, output=response.output)


def _build_prompt(
    text: str | None,
    image_base64: str | None,
    image_media_type: str,
) -> str | list[UserContent]:
    """Build the user prompt from text and/or image inputs."""
    if image_base64 is not None:
        parts: list[UserContent] = []
        if text:
            parts.append(text)
        parts.append(
            BinaryContent(
                data=base64.b64decode(image_base64),
                media_type=image_media_type,
            )
        )
        return parts
    # text-only
    assert text is not None  # validator on request schema guarantees this
    return text
