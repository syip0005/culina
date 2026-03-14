from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from pydantic_ai.exceptions import UsageLimitExceeded
from pydantic_ai.messages import ModelMessage, UserContent
from pydantic_ai.usage import UsageLimits

from culina_backend.ai.agent import search_agent
from culina_backend.ai.model.follow_up import FollowUpQuestion
from culina_backend.model import SearchNutritionResult


@dataclass(frozen=True, slots=True)
class LookupResponse:
    """Result of a nutrition lookup call."""

    output: SearchNutritionResult | FollowUpQuestion
    """The agent's structured output."""

    messages: list[ModelMessage]
    """Full conversation history after this turn (pass back on next call)."""


class NutritionLookup:
    """Stateless nutrition lookup — caller owns conversation history."""

    async def send(
        self,
        user_prompt: str | Sequence[UserContent],
        *,
        message_history: list[ModelMessage] | None = None,
    ) -> LookupResponse:
        """Send a message and get back nutrition data or a follow-up question.

        Args:
            user_prompt: Text query or multimodal content (text + images).
            message_history: Previous conversation turns (None for first message).

        Returns:
            LookupResponse with the agent output and updated message history.
        """
        try:
            result = await search_agent.run(
                user_prompt,
                message_history=message_history,
                usage_limits=UsageLimits(tool_calls_limit=5),
            )
        except UsageLimitExceeded:
            fallback = FollowUpQuestion(
                follow_up_question=(
                    "I couldn't find reliable nutrition info within my search limit. "
                    "Could you try being more specific, or rephrase your request?"
                ),
                follow_up_buttons=["Try again", "Be more specific"],
            )
            return LookupResponse(
                output=fallback,
                messages=message_history or [],
            )
        return LookupResponse(
            output=result.output,
            messages=result.all_messages(),
        )
