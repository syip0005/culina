from pydantic import BaseModel


class FollowUpQuestion(BaseModel):
    """A clarifying question the agent asks when the user's request is ambiguous."""

    follow_up_question: str
    """The clarifying question to ask the user."""

    follow_up_buttons: list[str] = []
    """Quick-reply button labels the user can tap instead of typing (may be empty)."""
