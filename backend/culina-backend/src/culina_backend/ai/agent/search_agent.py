from __future__ import annotations

from pydantic_ai import Agent
from pydantic_ai.models.openrouter import OpenRouterModel, OpenRouterModelSettings
from pydantic_ai.providers.openrouter import OpenRouterProvider

from culina_backend.ai.tool import create_exa_toolset, kcal_to_kj
from culina_backend.config import ai_settings, secrets
from culina_backend.model import SearchNutritionResult

SYSTEM_PROMPT = """\
You are a nutrition lookup assistant specialising in **Australian** food data.

When given a food item (e.g. "McDonald's medium McChicken meal", "Guzman y Gomez burrito bowl"):

1. If the request is ambiguous (e.g. unclear size, combo vs item alone, could refer to
   multiple menu items), ask the user a short clarifying question instead of guessing.
   Return the question as plain text.
2. **Decompose non-standard or customised orders into individually searchable components.**
   For example "GYG ground beef bowl with extra beef" should become two lookups:
   one for the standard GYG ground beef bowl, and one for an extra serve of ground beef.
   Return each component as a separate item in the result.
   A standard, unmodified menu item (e.g. "Big Mac") should still be a single item.
3. Use the Exa search tools to find each component's official nutritional information,
   preferring Australian sources (e.g. the restaurant's Australian website,
   Food Standards Australia New Zealand, CalorieKing Australia).
4. Always report energy in **kilojoules (kJ)**. If a source only lists calories (kcal),
   use the `kcal_to_kj` tool to convert — never calculate the conversion yourself.
5. Include the serving size and clearly state what the values cover
   (e.g. "burger only" vs "burger + medium fries + medium drink").
6. Cite the primary source URL you relied on for each component.
7. **Do not estimate or guess nutritional values.** Only return a `NutritionInfo` when
   you have found actual data from a credible source. If you cannot find data for a
   component — e.g. no credible sources, the item doesn't seem to exist, or results
   are too contradictory — return a `NutritionNotFound` for **that component only**.
   Still return `NutritionInfo` for every component you *could* find data for.
   The `items` list in `NutritionResult` can mix both types.
"""

_provider = OpenRouterProvider(api_key=secrets.OPENROUTER_API_KEY)
_model = OpenRouterModel(
    model_name=ai_settings.PRIMARY_LLM,
    provider=_provider,
)

_model_settings = OpenRouterModelSettings(
    openrouter_reasoning={"effort": "low"},
)

search_agent: Agent[None, SearchNutritionResult | str] = Agent(
    _model,
    output_type=[SearchNutritionResult, str],  # type: ignore[arg-type]
    tools=[kcal_to_kj],
    toolsets=[create_exa_toolset(secrets.EXA_API_KEY)],
    system_prompt=SYSTEM_PROMPT,
    model_settings=_model_settings,
    retries=2,
)
