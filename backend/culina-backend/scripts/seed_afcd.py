"""Download, process, and seed AFCD nutrition data into the database.

Combines the download, processing, and database seeding steps into one script.

Usage:
    uv run python scripts/seed_afcd.py              # download, process, seed
    uv run python scripts/seed_afcd.py --skip-download  # reuse existing Excel files
    uv run python scripts/seed_afcd.py --reset       # delete existing AFCD entries first
"""

from __future__ import annotations

import argparse
import asyncio
import json
import subprocess
import sys
from datetime import date
from pathlib import Path
from uuid import UUID

from sqlalchemy import delete, func, select

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from culina_backend.database.base import async_session, engine  # noqa: E402
from culina_backend.database.models import (  # noqa: E402
    NutritionEntryModel,
    UserModel,
)
from culina_backend.model.user_nutrition import SYSTEM_USER_ID  # noqa: E402

DATA_DIR = PROJECT_ROOT / "data" / "afcd"
JSON_FILE = DATA_DIR / "afcd_nutrition.json"
DOWNLOAD_SCRIPT = PROJECT_ROOT / "scripts" / "download_afcd.sh"
PROCESS_SCRIPT = PROJECT_ROOT / "scripts" / "process_afcd.py"


def download() -> None:
    """Run the download shell script."""
    print("\n=== Step 1: Downloading AFCD data ===")
    result = subprocess.run(["bash", str(DOWNLOAD_SCRIPT)], check=False)
    if result.returncode != 0:
        print("Download failed.", file=sys.stderr)
        sys.exit(1)


def process() -> None:
    """Run the processing script to convert Excel → JSON."""
    print("\n=== Step 2: Processing AFCD Excel → JSON ===")
    result = subprocess.run([sys.executable, str(PROCESS_SCRIPT)], check=False)
    if result.returncode != 0:
        print("Processing failed.", file=sys.stderr)
        sys.exit(1)


async def seed(reset: bool) -> None:
    """Load afcd_nutrition.json and upsert into the database."""
    print("\n=== Step 3: Seeding AFCD entries into database ===")

    if not JSON_FILE.exists():
        print(f"Error: {JSON_FILE} not found.", file=sys.stderr)
        sys.exit(1)

    entries = json.loads(JSON_FILE.read_text())
    print(f"Loaded {len(entries)} entries from {JSON_FILE.name}")

    async with async_session() as session:
        # Ensure system user exists
        system_user = (
            await session.execute(
                select(UserModel).where(UserModel.id == SYSTEM_USER_ID)
            )
        ).scalar_one_or_none()

        if system_user is None:
            session.add(
                UserModel(
                    id=SYSTEM_USER_ID,
                    external_id="system",
                    display_name="System",
                )
            )
            await session.commit()
            print("  Created system user.")

        if reset:
            # Delete user overrides of AFCD entries first (base_entry_id refs)
            afcd_ids_subq = (
                select(NutritionEntryModel.id).where(
                    NutritionEntryModel.user_id == SYSTEM_USER_ID,
                    NutritionEntryModel.source == "afcd",
                )
            ).scalar_subquery()
            deleted_overrides = (
                await session.execute(
                    delete(NutritionEntryModel).where(
                        NutritionEntryModel.base_entry_id.in_(afcd_ids_subq)
                    )
                )
            ).rowcount
            # Then delete the system AFCD entries themselves
            deleted_system = (
                await session.execute(
                    delete(NutritionEntryModel).where(
                        NutritionEntryModel.user_id == SYSTEM_USER_ID,
                        NutritionEntryModel.source == "afcd",
                    )
                )
            ).rowcount
            await session.commit()
            print(
                f"  Reset: deleted {deleted_system} system AFCD entries "
                f"and {deleted_overrides} user overrides."
            )

        # Check which afcd_food_keys already exist
        existing_keys = set(
            (
                await session.execute(
                    select(NutritionEntryModel.afcd_food_key).where(
                        NutritionEntryModel.user_id == SYSTEM_USER_ID,
                        NutritionEntryModel.source == "afcd",
                        NutritionEntryModel.afcd_food_key.isnot(None),
                    )
                )
            )
            .scalars()
            .all()
        )
        print(f"  {len(existing_keys)} AFCD entries already in database.")

        # Insert new entries
        inserted = 0
        skipped = 0
        for entry_data in entries:
            afcd_key = entry_data.get("afcd_food_key")
            if afcd_key and afcd_key in existing_keys:
                skipped += 1
                continue

            model = NutritionEntryModel(
                user_id=SYSTEM_USER_ID,
                food_item=entry_data["food_item"],
                brand=entry_data.get("brand", ""),
                source="afcd",
                source_url=entry_data.get("source_url"),
                serving_size=entry_data.get("serving_size", "100g"),
                energy_kj=entry_data.get("energy_kj"),
                protein_g=entry_data.get("protein_g"),
                fat_g=entry_data.get("fat_g"),
                carbs_g=entry_data.get("carbs_g"),
                afcd_food_key=afcd_key,
                date_retrieved=date.today(),
            )
            session.add(model)
            inserted += 1

        await session.commit()

        total = (
            await session.execute(
                select(func.count()).where(
                    NutritionEntryModel.user_id == SYSTEM_USER_ID,
                    NutritionEntryModel.source == "afcd",
                )
            )
        ).scalar()

        print(f"  Inserted {inserted}, skipped {skipped} duplicates.")
        print(f"  Total AFCD entries in database: {total}")

    await engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Download, process, and seed AFCD nutrition data."
    )
    parser.add_argument(
        "--skip-download",
        action="store_true",
        help="Skip downloading Excel files (reuse existing)",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Delete existing AFCD entries before seeding",
    )
    args = parser.parse_args()

    if not args.skip_download:
        download()

    process()
    asyncio.run(seed(args.reset))

    print("\nDone!")


if __name__ == "__main__":
    main()
