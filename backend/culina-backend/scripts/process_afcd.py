"""Process AFCD Nutrient Excel file into a JSON array of NutritionInfo entries."""

import json
import sys
from pathlib import Path

import pandas as pd

# Ensure the project src is importable
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from culina_backend.model.nutrition import NutritionInfo, NutritionSource  # noqa: E402

DATA_DIR = PROJECT_ROOT / "data" / "afcd"
NUTRIENT_FILE = DATA_DIR / "AFCD Release 3 - Nutrient profiles.xlsx"
OUTPUT_FILE = DATA_DIR / "afcd_nutrition.json"

SHEET_NAME = "All solids & liquids per 100 g"
HEADER_ROW = 2  # 0-indexed; row 3 in Excel

AFCD_SOURCE_URL = (
    "https://www.foodstandards.gov.au/science-data/"
    "monitoringnutrients/afcd/australian-food-composition-database-release-3"
)

# Column mapping: Excel column name → our field name
COLUMN_MAP = {
    "Food Name": "food_item",
    "Energy with dietary fibre, equated \n(kJ)": "energy_kj",
    "Protein \n(g)": "protein_g",
    "Fat, total \n(g)": "fat_g",
    "Available carbohydrate, without sugar alcohols \n(g)": "carbs_g",
}


def main() -> None:
    if not NUTRIENT_FILE.exists():
        print(
            f"Error: {NUTRIENT_FILE} not found. Run scripts/download_afcd.sh first.",
            file=sys.stderr,
        )
        sys.exit(1)

    print(f"Reading {NUTRIENT_FILE} ...")
    df = pd.read_excel(
        NUTRIENT_FILE,
        sheet_name=SHEET_NAME,
        header=HEADER_ROW,
        engine="openpyxl",
    )

    # Keep only the columns we need
    missing_cols = [c for c in COLUMN_MAP if c not in df.columns]
    if missing_cols:
        print(f"Error: missing columns: {missing_cols}", file=sys.stderr)
        print(f"Available columns: {list(df.columns)}", file=sys.stderr)
        sys.exit(1)

    df = df[list(COLUMN_MAP.keys())].rename(columns=COLUMN_MAP)

    # Convert numeric columns and drop rows with missing macros
    numeric_cols = ["energy_kj", "protein_g", "fat_g", "carbs_g"]
    df[numeric_cols] = df[numeric_cols].apply(pd.to_numeric, errors="coerce")
    before = len(df)
    df = df.dropna(subset=numeric_cols)
    print(f"Dropped {before - len(df)} rows with missing macros ({len(df)} remaining)")

    # Build NutritionInfo entries
    entries: list[dict] = []
    for _, row in df.iterrows():
        info = NutritionInfo(
            food_item=str(row["food_item"]).strip(),
            brand="",
            source_url=AFCD_SOURCE_URL,
            serving_size="100g",
            energy_kj=round(float(row["energy_kj"]), 1),
            protein_g=round(float(row["protein_g"]), 1),
            fat_g=round(float(row["fat_g"]), 1),
            carbs_g=round(float(row["carbs_g"]), 1),
            source=NutritionSource.afcd,
        )
        entries.append(info.model_dump(mode="json"))

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(json.dumps(entries, indent=2, ensure_ascii=False))
    print(f"Wrote {len(entries)} entries to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
