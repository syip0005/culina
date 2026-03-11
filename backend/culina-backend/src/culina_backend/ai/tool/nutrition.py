from __future__ import annotations

KCAL_TO_KJ = 4.184


def kcal_to_kj(kcal: float) -> float:
    """Convert kilocalories (kcal) to kilojoules (kJ).

    Args:
        kcal: Energy value in kilocalories.

    Returns:
        Energy value in kilojoules, rounded to 1 decimal place.
    """
    return round(kcal * KCAL_TO_KJ, 1)
