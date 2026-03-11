from __future__ import annotations

from pydantic_ai.common_tools.exa import ExaToolset


def create_exa_toolset(api_key: str) -> ExaToolset:
    """Create an Exa toolset configured for nutrition searches."""
    return ExaToolset(
        api_key=api_key,
        num_results=5,
        max_characters=3000,
        include_search=True,
        include_get_contents=True,
        include_find_similar=False,
        include_answer=False,
    )
