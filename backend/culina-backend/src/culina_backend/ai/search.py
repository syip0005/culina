from __future__ import annotations

from pydantic_ai.messages import ModelMessage
from pydantic_ai.usage import UsageLimits

from culina_backend.ai.agent import search_agent
from culina_backend.ai.model.follow_up import FollowUpQuestion
from culina_backend.model import SearchNutritionResult


class NutritionSearch:
    """Stateful nutrition search that supports multi-turn clarification."""

    def __init__(self) -> None:
        self._history: list[ModelMessage] = []

    async def send(self, message: str) -> SearchNutritionResult | FollowUpQuestion:
        """Send a message and get back nutrition data (may include not-found components) or a follow-up question."""
        result = await search_agent.run(
            message,
            message_history=self._history or None,
            usage_limits=UsageLimits(tool_calls_limit=5),
        )
        self._history = result.all_messages()
        return result.output

    def reset(self) -> None:
        """Clear conversation history."""
        self._history = []
