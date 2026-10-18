"""Deterministic candidate retrieval and metadata extraction.

Phase 3: Filter Engine
- get_candidates(): Rule-based retrieval with multi-tier fallback chain.
- extract_metadata(): Dynamic dropdown population from dataset.
"""

import pandas as pd
from src.config import settings

# Budget tier ordering for ±1 tier tolerance
BUDGET_ORDER = ["Low", "Medium", "High"]

# Minimum candidate count before fallback is triggered
MIN_STRICT_RESULTS = 3


def _apply_city_filter(df: pd.DataFrame, city: str) -> pd.Series:
    """Return boolean mask for case-insensitive city match."""
    return df["city"].astype(str).str.lower() == city.strip().lower()


def _apply_cuisine_filter(mask: pd.Series, df: pd.DataFrame, cuisines: list[str]) -> pd.Series:
    """Narrow mask to rows whose cuisines_list overlaps any requested cuisine."""
    if not cuisines:
        return mask
    cuisine_lower = [c.strip().lower() for c in cuisines]
    cuisine_mask = df["cuisines_list"].apply(
        lambda lst: any(c in lst for c in cuisine_lower)
        if isinstance(lst, list) else False
    )
    return mask & cuisine_mask


def _apply_budget_filter(mask: pd.Series, df: pd.DataFrame, budget: str, tolerance: int = 1) -> pd.Series:
    """Narrow mask to budget tier with optional ±tolerance tiers."""
    if "budget_tier" not in df.columns or budget not in BUDGET_ORDER:
        return mask
    idx = BUDGET_ORDER.index(budget)
    allowed = BUDGET_ORDER[max(0, idx - tolerance): idx + 1 + tolerance]
    return mask & df["budget_tier"].astype(str).isin(allowed)


def _apply_rating_filter(mask: pd.Series, df: pd.DataFrame, min_rating: float) -> pd.Series:
    """Narrow mask to rows meeting or exceeding the minimum rating."""
    if "rating" not in df.columns:
        return mask
    return mask & (df["rating"] >= min_rating)


def _sort_and_truncate(df: pd.DataFrame, max_results: int) -> pd.DataFrame:
    """Sort by popularity_score descending and return top max_results rows."""
    if "popularity_score" in df.columns:
        df = df.sort_values("popularity_score", ascending=False)
    return df.head(max_results)


def _apply_area_filter(mask: pd.Series, df: pd.DataFrame, area: str | None) -> pd.Series:
    """Narrow mask to rows matching specific neighborhood area if specified."""
    if not area or area.strip().lower() in ["", "all", "all areas", "any"]:
        return mask
    if "location" not in df.columns:
        return mask
    return mask & (df["location"].astype(str).str.lower() == area.strip().lower())


def get_candidates(
    df: pd.DataFrame,
    city: str,
    cuisines: list[str],
    budget: str,
    min_rating: float,
    area: str | None = None,
    max_results: int = settings.MAX_CANDIDATES,
) -> pd.DataFrame:
    """Retrieve top candidate restaurants using a deterministic filter chain.

    Filter chain (applied in order, strictest first):
      1. City match (case-insensitive, mandatory)
      2. Area / locality match (optional neighborhood filter)
      3. Cuisine overlap (any match from requested list, optional)
      4. Budget tier (±1 tier tolerance)
      5. Minimum rating

    Fallback chain (triggers when strict result count < MIN_STRICT_RESULTS):
      Pass 1 — Relax cuisine constraint (keep city + area + budget + rating).
      Pass 2 — Relax budget constraint as well (keep city + area + rating only).
      Pass 3 — Relax area constraint if specified (keep city + rating).
      Pass 4 — Return top-rated restaurants in city regardless of cuisine/budget.

    Returns:
        DataFrame of up to max_results candidates sorted by popularity_score DESC.
    """
    if df.empty:
        return df

    # ── Strict pass ──────────────────────────────────────────────────────────
    city_mask = _apply_city_filter(df, city)
    strict_mask = city_mask.copy()
    strict_mask = _apply_area_filter(strict_mask, df, area)
    strict_mask = _apply_cuisine_filter(strict_mask, df, cuisines)
    strict_mask = _apply_budget_filter(strict_mask, df, budget)
    strict_mask = _apply_rating_filter(strict_mask, df, min_rating)

    strict_results = df[strict_mask]
    if len(strict_results) >= MIN_STRICT_RESULTS:
        return _sort_and_truncate(strict_results, max_results)

    # ── Fallback Pass 1: relax cuisine ────────────────────────────────────────
    if cuisines:
        pass1_mask = city_mask.copy()
        pass1_mask = _apply_area_filter(pass1_mask, df, area)
        pass1_mask = _apply_budget_filter(pass1_mask, df, budget)
        pass1_mask = _apply_rating_filter(pass1_mask, df, min_rating)
        pass1_results = df[pass1_mask]
        if len(pass1_results) >= MIN_STRICT_RESULTS:
            return _sort_and_truncate(pass1_results, max_results)

    # ── Fallback Pass 2: relax cuisine + budget ───────────────────────────────
    pass2_mask = city_mask.copy()
    pass2_mask = _apply_area_filter(pass2_mask, df, area)
    pass2_mask = _apply_rating_filter(pass2_mask, df, min_rating)
    pass2_results = df[pass2_mask]
    if len(pass2_results) >= MIN_STRICT_RESULTS:
        return _sort_and_truncate(pass2_results, max_results)

    # ── Fallback Pass 3: relax area if specified (keep rating) ────────────────
    if area and area.strip().lower() not in ["", "all", "all areas", "any"]:
        pass3_mask = city_mask.copy()
        pass3_mask = _apply_rating_filter(pass3_mask, df, min_rating)
        pass3_results = df[pass3_mask]
        if len(pass3_results) >= MIN_STRICT_RESULTS:
            return _sort_and_truncate(pass3_results, max_results)

    # ── Fallback Pass 4: top-rated in city (ignore cuisine/budget/rating) ─────
    city_only_results = df[city_mask]
    return _sort_and_truncate(city_only_results, max_results)


def extract_metadata(df: pd.DataFrame) -> dict:
    """Extract distinct cities, neighborhood areas, and cuisines for frontend dropdowns.

    Returns:
        dict with keys: cities, areas, cuisines, budget_tiers, rating_range.
    """
    if df.empty:
        return {
            "cities": [],
            "areas": [],
            "cuisines": [],
            "budget_tiers": BUDGET_ORDER,
            "rating_range": {"min": 1.0, "max": 5.0},
        }

    cities = sorted(
        df["city"].dropna().astype(str).str.title().unique().tolist()
    )
    areas = sorted(
        df["location"].dropna().astype(str).str.strip().str.title().unique().tolist()
    ) if "location" in df.columns else []

    all_cuisines = sorted(set(
        c
        for lst in df.get("cuisines_list", pd.Series(dtype=object))
        for c in (lst if isinstance(lst, list) else [])
        if isinstance(c, str) and c.strip()
    ))
    return {
        "cities": cities,
        "areas": areas,
        "cuisines": all_cuisines,
        "budget_tiers": BUDGET_ORDER,
        "rating_range": {"min": 1.0, "max": 5.0},
    }
