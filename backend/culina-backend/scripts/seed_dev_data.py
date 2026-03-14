"""Seed the dev database with realistic test data.

Usage:
    uv run python scripts/seed_dev_data.py           # insert if not present
    uv run python scripts/seed_dev_data.py --reset    # wipe and re-seed
"""

from __future__ import annotations

import argparse
import asyncio
from datetime import date, datetime, timezone
from uuid import UUID

from sqlalchemy import select, text

from culina_backend.database.base import async_session, engine
from culina_backend.database.models import (
    MealItem,
    MealModel,
    NutritionEntryModel,
    UserModel,
    UserSettings,
)
from culina_backend.model.user_nutrition import SYSTEM_USER_ID

# ---------------------------------------------------------------------------
# Fixed IDs for deterministic seeding
# ---------------------------------------------------------------------------
USER_ALICE_ID = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
USER_BOB_ID = UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")

SYSTEM_ENTRIES: list[dict] = [
    dict(
        food_item="Whole Milk",
        brand="",
        serving_size="250 mL",
        energy_kj=690.0,
        protein_g=8.3,
        fat_g=9.0,
        carbs_g=12.0,
        source="afcd",
        afcd_food_key="01-001",
    ),
    dict(
        food_item="Cheddar Cheese",
        brand="",
        serving_size="30 g",
        energy_kj=512.0,
        protein_g=7.5,
        fat_g=10.3,
        carbs_g=0.1,
        source="afcd",
        afcd_food_key="01-021",
    ),
    dict(
        food_item="Chicken Breast",
        brand="",
        serving_size="100 g",
        energy_kj=460.0,
        protein_g=31.0,
        fat_g=3.6,
        carbs_g=0.0,
        source="afcd",
        afcd_food_key="05-064",
    ),
    dict(
        food_item="White Rice (cooked)",
        brand="",
        serving_size="150 g",
        energy_kj=870.0,
        protein_g=4.1,
        fat_g=0.5,
        carbs_g=47.0,
        source="afcd",
        afcd_food_key="20-006",
    ),
    dict(
        food_item="Banana",
        brand="",
        serving_size="1 medium (118 g)",
        energy_kj=370.0,
        protein_g=1.3,
        fat_g=0.4,
        carbs_g=23.0,
        source="afcd",
        afcd_food_key="09-040",
    ),
    dict(
        food_item="Rolled Oats",
        brand="",
        serving_size="40 g (dry)",
        energy_kj=620.0,
        protein_g=5.3,
        fat_g=3.2,
        carbs_g=24.0,
        source="afcd",
        afcd_food_key="08-120",
    ),
    dict(
        food_item="Broccoli",
        brand="",
        serving_size="100 g",
        energy_kj=140.0,
        protein_g=2.8,
        fat_g=0.4,
        carbs_g=7.2,
        source="afcd",
        afcd_food_key="11-090",
    ),
    dict(
        food_item="Salmon Fillet",
        brand="",
        serving_size="100 g",
        energy_kj=840.0,
        protein_g=20.0,
        fat_g=13.0,
        carbs_g=0.0,
        source="afcd",
        afcd_food_key="15-076",
    ),
    dict(
        food_item="Whole Wheat Bread",
        brand="",
        serving_size="1 slice (36 g)",
        energy_kj=350.0,
        protein_g=3.6,
        fat_g=1.2,
        carbs_g=17.0,
        source="afcd",
        afcd_food_key="18-075",
    ),
    dict(
        food_item="Egg (boiled)",
        brand="",
        serving_size="1 large (50 g)",
        energy_kj=310.0,
        protein_g=6.3,
        fat_g=5.3,
        carbs_g=0.6,
        source="afcd",
        afcd_food_key="01-129",
    ),
]

ALICE_ENTRIES: list[dict] = [
    dict(
        food_item="Flat White",
        brand="Campos Coffee",
        serving_size="1 cup",
        energy_kj=450.0,
        protein_g=6.0,
        fat_g=7.0,
        carbs_g=8.0,
        source="manual",
    ),
    dict(
        food_item="Protein Bar",
        brand="YoPRO",
        serving_size="1 bar (55 g)",
        energy_kj=780.0,
        protein_g=15.0,
        fat_g=6.0,
        carbs_g=25.0,
        source="search",
    ),
    dict(
        food_item="Greek Yoghurt",
        brand="Chobani",
        serving_size="170 g",
        energy_kj=580.0,
        protein_g=15.0,
        fat_g=5.0,
        carbs_g=12.0,
        source="search",
    ),
    dict(
        food_item="Avocado Toast",
        brand="",
        serving_size="2 slices",
        energy_kj=1250.0,
        protein_g=8.0,
        fat_g=18.0,
        carbs_g=38.0,
        source="manual",
    ),
    dict(
        food_item="Chicken Salad Bowl",
        brand="",
        serving_size="1 bowl (~350 g)",
        energy_kj=1600.0,
        protein_g=35.0,
        fat_g=12.0,
        carbs_g=40.0,
        source="manual",
    ),
]

BOB_ENTRIES: list[dict] = [
    dict(
        food_item="Peanut Butter",
        brand="Mayver's",
        serving_size="1 tbsp (20 g)",
        energy_kj=500.0,
        protein_g=5.0,
        fat_g=10.0,
        carbs_g=3.0,
        source="search",
    ),
    dict(
        food_item="Tim Tam",
        brand="Arnott's",
        serving_size="2 biscuits (36 g)",
        energy_kj=750.0,
        protein_g=2.0,
        fat_g=8.5,
        carbs_g=24.0,
        source="manual",
    ),
    dict(
        food_item="Vegemite on Toast",
        brand="",
        serving_size="1 slice",
        energy_kj=420.0,
        protein_g=4.5,
        fat_g=1.5,
        carbs_g=18.0,
        source="manual",
    ),
    dict(
        food_item="Beef Steak",
        brand="",
        serving_size="200 g",
        energy_kj=1100.0,
        protein_g=50.0,
        fat_g=10.0,
        carbs_g=0.0,
        source="search",
    ),
    dict(
        food_item="Kombucha",
        brand="Remedy",
        serving_size="330 mL",
        energy_kj=35.0,
        protein_g=0.0,
        fat_g=0.0,
        carbs_g=2.0,
        source="search",
    ),
]


async def _seed(reset: bool) -> None:
    async with async_session() as session:
        if reset:
            # Delete in dependency order
            await session.execute(text("DELETE FROM meal_items"))
            await session.execute(text("DELETE FROM meal_photos"))
            await session.execute(text("DELETE FROM meals"))
            await session.execute(text("DELETE FROM nutrition_entries"))
            await session.execute(text("DELETE FROM user_settings"))
            await session.execute(text("DELETE FROM users"))
            await session.commit()
            print("Wiped all tables.")

        # --- Users ---
        existing = (await session.execute(select(UserModel.id))).scalars().all()
        existing_ids = set(existing)

        users = [
            (SYSTEM_USER_ID, "system", None, "System"),
            (USER_ALICE_ID, "alice-ext-id", "alice@example.com", "Alice"),
            (USER_BOB_ID, "bob-ext-id", "bob@example.com", "Bob"),
        ]
        for uid, ext_id, email, name in users:
            if uid not in existing_ids:
                session.add(
                    UserModel(
                        id=uid, external_id=ext_id, email=email, display_name=name
                    )
                )
                print(f"  Created user {name} ({uid})")
        await session.commit()

        # --- User Settings ---
        for uid, settings_kwargs in [
            (
                USER_ALICE_ID,
                dict(
                    daily_energy_target_kj=8000.0,
                    daily_protein_target_g=120.0,
                    daily_fat_target_g=65.0,
                    daily_carbs_target_g=250.0,
                    timezone="Australia/Sydney",
                ),
            ),
            (
                USER_BOB_ID,
                dict(
                    daily_energy_target_kj=10000.0,
                    daily_protein_target_g=150.0,
                    daily_fat_target_g=80.0,
                    daily_carbs_target_g=300.0,
                    timezone="Australia/Melbourne",
                ),
            ),
        ]:
            existing_setting = (
                await session.execute(
                    select(UserSettings).where(UserSettings.user_id == uid)
                )
            ).scalar_one_or_none()
            if existing_setting is None:
                session.add(UserSettings(user_id=uid, **settings_kwargs))
                print(f"  Created settings for {uid}")
        await session.commit()

        # --- Nutrition Entries ---
        existing_entries = (
            await session.execute(
                select(NutritionEntryModel.food_item, NutritionEntryModel.user_id)
            )
        ).all()
        existing_set = {(r[0], r[1]) for r in existing_entries}

        entry_models: list[NutritionEntryModel] = []

        for entry_data in SYSTEM_ENTRIES:
            if (entry_data["food_item"], SYSTEM_USER_ID) not in existing_set:
                m = NutritionEntryModel(
                    user_id=SYSTEM_USER_ID,
                    date_retrieved=date(2025, 1, 1),
                    **entry_data,
                )
                session.add(m)
                entry_models.append(m)
                print(f"  Created system entry: {entry_data['food_item']}")

        for uid, entries in [
            (USER_ALICE_ID, ALICE_ENTRIES),
            (USER_BOB_ID, BOB_ENTRIES),
        ]:
            for entry_data in entries:
                if (entry_data["food_item"], uid) not in existing_set:
                    m = NutritionEntryModel(
                        user_id=uid,
                        date_retrieved=date.today(),
                        **entry_data,
                    )
                    session.add(m)
                    entry_models.append(m)
                    print(f"  Created user entry: {entry_data['food_item']} for {uid}")

        await session.commit()

        # Refresh to get IDs
        for m in entry_models:
            await session.refresh(m)

        # --- User override of system entry ---
        # Alice overrides "Whole Milk" with her preferred brand
        milk = (
            await session.execute(
                select(NutritionEntryModel).where(
                    NutritionEntryModel.food_item == "Whole Milk",
                    NutritionEntryModel.user_id == SYSTEM_USER_ID,
                )
            )
        ).scalar_one_or_none()

        if milk is not None:
            alice_override = (
                await session.execute(
                    select(NutritionEntryModel).where(
                        NutritionEntryModel.base_entry_id == milk.id,
                        NutritionEntryModel.user_id == USER_ALICE_ID,
                    )
                )
            ).scalar_one_or_none()

            if alice_override is None:
                override = NutritionEntryModel(
                    user_id=USER_ALICE_ID,
                    food_item="Whole Milk",
                    brand="Norco",
                    serving_size="250 mL",
                    energy_kj=680.0,
                    protein_g=8.0,
                    fat_g=8.5,
                    carbs_g=12.5,
                    source="afcd",
                    afcd_food_key="01-001",
                    base_entry_id=milk.id,
                    date_retrieved=date.today(),
                    notes="Alice's preferred brand — slightly different macros",
                )
                session.add(override)
                await session.commit()
                await session.refresh(override)
                print(
                    f"  Created Alice's override of Whole Milk (base_entry_id={milk.id})"
                )

        # --- Meals ---
        # Grab some entry IDs
        alice_entries = (
            (
                await session.execute(
                    select(NutritionEntryModel).where(
                        NutritionEntryModel.user_id == USER_ALICE_ID
                    )
                )
            )
            .scalars()
            .all()
        )

        bob_entries = (
            (
                await session.execute(
                    select(NutritionEntryModel).where(
                        NutritionEntryModel.user_id == USER_BOB_ID
                    )
                )
            )
            .scalars()
            .all()
        )

        existing_meals = (
            (await session.execute(select(MealModel.user_id))).scalars().all()
        )

        if USER_ALICE_ID not in existing_meals and alice_entries:
            now = datetime.now(timezone.utc)
            meal = MealModel(
                user_id=USER_ALICE_ID,
                meal_type="breakfast",
                name="Morning fuel",
                eaten_at=now,
                notes="Quick pre-gym breakfast",
            )
            session.add(meal)
            await session.commit()
            await session.refresh(meal)

            # Add a couple items
            for entry in alice_entries[:2]:
                session.add(
                    MealItem(meal_id=meal.id, nutrition_entry_id=entry.id, quantity=1.0)
                )
            await session.commit()
            print(
                f"  Created breakfast meal for Alice with {min(2, len(alice_entries))} items"
            )

        if USER_BOB_ID not in existing_meals and bob_entries:
            now = datetime.now(timezone.utc)
            meal = MealModel(
                user_id=USER_BOB_ID,
                meal_type="lunch",
                name="Arvo snack",
                eaten_at=now,
            )
            session.add(meal)
            await session.commit()
            await session.refresh(meal)

            for entry in bob_entries[:2]:
                session.add(
                    MealItem(meal_id=meal.id, nutrition_entry_id=entry.id, quantity=1.0)
                )
            await session.commit()
            print(f"  Created lunch meal for Bob with {min(2, len(bob_entries))} items")

    print("\nSeed complete.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed the dev database.")
    parser.add_argument(
        "--reset", action="store_true", help="Wipe tables before seeding"
    )
    args = parser.parse_args()

    asyncio.run(_seed(args.reset))

    # Dispose engine to avoid asyncio warnings
    asyncio.run(engine.dispose())


if __name__ == "__main__":
    main()
