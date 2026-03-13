#!/usr/bin/env bash
# Download AFCD (Australian Food Composition Database) Release 3 Excel files.
set -euo pipefail

DATA_DIR="$(cd "$(dirname "$0")/.." && pwd)/data/afcd"
mkdir -p "$DATA_DIR"

BASE_URL="https://www.foodstandards.gov.au/sites/default/files/2025-12"
files=(
  "AFCD%20Release%203%20-%20Food%20Details.xlsx"
  "AFCD%20Release%203%20-%20Nutrient%20profiles.xlsx"
)

for file in "${files[@]}"; do
  echo "Downloading $file ..."
  curl -fSL -o "$DATA_DIR/$(printf '%b' "${file//%/\\x}")" "$BASE_URL/$file"
done

echo "Done. Files saved to $DATA_DIR"
