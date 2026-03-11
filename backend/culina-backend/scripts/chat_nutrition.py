"""Interactive REPL for testing NutritionSearch."""

import asyncio

from culina_backend.ai.search import NutritionSearch
from culina_backend.model import (
    NutritionInfo,
    SearchNutritionNotFound,
    SearchNutritionResult,
)


def _print_info(item: NutritionInfo, prefix: str = "") -> None:
    print(f"\n  {prefix}{item.food_item}")
    print(f"  Serving:  {item.serving_size}")
    print(f"  Energy:   {item.energy_kj:.0f} kJ")
    print(f"  Protein:  {item.protein_g:.1f} g")
    print(f"  Fat:      {item.fat_g:.1f} g")
    print(f"  Carbs:    {item.carbs_g:.1f} g")
    if item.notes:
        print(f"  Notes:    {item.notes}")
    print(f"  Source:   {item.source_url}")


def _print_not_found(item: SearchNutritionNotFound, prefix: str = "") -> None:
    print(f"\n  {prefix}Not found: {item.query}")
    print(f"  Reason:   {item.reason}")
    if item.suggestions:
        print("  Try instead:")
        for s in item.suggestions:
            print(f"    - {s}")


async def main() -> None:
    search = NutritionSearch()
    print("Nutrition Search REPL  (type 'quit' to exit, 'reset' to clear history)\n")

    while True:
        try:
            message = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if not message:
            continue
        if message.lower() == "quit":
            break
        if message.lower() == "reset":
            search.reset()
            print("-- history cleared --\n")
            continue

        result = await search.send(message)

        if isinstance(result, SearchNutritionResult):
            multi = len(result.items) > 1

            for i, item in enumerate(result.items, 1):
                prefix = f"[{i}/{len(result.items)}] " if multi else ""
                if isinstance(item, NutritionInfo):
                    _print_info(item, prefix)
                else:
                    _print_not_found(item, prefix)

            found = [it for it in result.items if isinstance(it, NutritionInfo)]
            if multi and found:
                print("\n  --- Total (found items only) ---")
                print(f"  Energy:   {sum(it.energy_kj for it in found):.0f} kJ")
                print(f"  Protein:  {sum(it.protein_g for it in found):.1f} g")
                print(f"  Fat:      {sum(it.fat_g for it in found):.1f} g")
                print(f"  Carbs:    {sum(it.carbs_g for it in found):.1f} g")
        else:
            print(f"\n  {result}")

        print()


if __name__ == "__main__":
    asyncio.run(main())
