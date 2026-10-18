"""Unit tests for Phase 3: Deterministic Candidate Filter Engine.

Covers:
- City filter (case-insensitive)
- Cuisine overlap filter (list-based, not exact string)
- Budget tier filter (±1 tier tolerance)
- Minimum rating filter
- Fallback chain: cuisine → budget → city-only
- extract_metadata() non-empty returns
"""

import pandas as pd
import pytest
from src.engine.filter import get_candidates, extract_metadata, BUDGET_ORDER, MIN_STRICT_RESULTS


# ─── Fixtures ────────────────────────────────────────────────────────────────

@pytest.fixture
def sample_df():
    """Small deterministic dataset for filter unit tests."""
    return pd.DataFrame({
        "name": [
            "Pasta Palace",    # bangalore | italian+pasta | Medium | 4.5
            "Curry House",     # bangalore | north indian  | Low    | 4.2
            "Sushi World",     # delhi     | japanese      | High   | 4.8
            "Burger Barn",     # bangalore | american      | Low    | 3.8
            "Biryani Bliss",   # bangalore | north indian  | Medium | 4.1
        ],
        "city": ["bangalore", "bangalore", "delhi", "bangalore", "bangalore"],
        "location": ["Indiranagar", "Koramangala", "Connaught Place", "HSR Layout", "BTM Layout"],
        "cuisines": ["Italian, Pasta", "North Indian", "Japanese", "American", "North Indian, Biryani"],
        "cuisines_list": [
            ["italian", "pasta"],
            ["north indian"],
            ["japanese"],
            ["american"],
            ["north indian", "biryani"],
        ],
        "rating": [4.5, 4.2, 4.8, 3.8, 4.1],
        "cost": [1200, 500, 2500, 400, 700],
        "budget_tier": ["Medium", "Low", "High", "Low", "Medium"],
        "popularity_score": [8.0, 6.0, 9.0, 5.0, 7.0],
    })


@pytest.fixture
def sparse_df():
    """Dataset where strict filters will return fewer than MIN_STRICT_RESULTS rows."""
    return pd.DataFrame({
        "name": ["Only One", "Another One"],
        "city": ["mumbai", "mumbai"],
        "location": ["Bandra", "Andheri"],
        "cuisines": ["Chinese", "Continental"],
        "cuisines_list": [["chinese"], ["continental"]],
        "rating": [4.5, 4.3],
        "cost": [800, 900],
        "budget_tier": ["Medium", "Medium"],
        "popularity_score": [7.0, 6.5],
    })


# ─── 3.1 Core Filter Tests ───────────────────────────────────────────────────

class TestCityFilter:
    def test_city_filter_case_insensitive(self, sample_df):
        """City match must be case-insensitive."""
        result = get_candidates(sample_df, "Bangalore", [], "Medium", 3.0)
        assert not result.empty
        assert all(r == "bangalore" for r in result["city"])

    def test_city_filter_uppercase(self, sample_df):
        result = get_candidates(sample_df, "BANGALORE", [], "Medium", 3.0)
        assert not result.empty
        assert all(r == "bangalore" for r in result["city"])

    def test_city_filter_excludes_other_cities(self, sample_df):
        result = get_candidates(sample_df, "bangalore", [], "Medium", 3.0)
        assert "Sushi World" not in result["name"].values

    def test_city_no_match_returns_empty(self, sample_df):
        result = get_candidates(sample_df, "Chennai", [], "Medium", 3.0)
        assert result.empty


class TestCuisineFilter:
    def test_cuisine_overlap_match(self, sample_df):
        """Cuisine filter uses list overlap, not exact string match."""
        result = get_candidates(sample_df, "bangalore", ["italian"], "Medium", 3.0)
        assert "Pasta Palace" in result["name"].values

    def test_cuisine_no_match_excludes_row(self):
        """When strict pass returns >= MIN_STRICT_RESULTS, non-matching cuisine is excluded."""
        # Build a df where "italian" + "Medium" + rating 3.0 yields exactly 3+ strict results
        df = pd.DataFrame({
            "name": ["Pasta Place", "Pizza Corner", "Focaccia", "Curry Den"],
            "city": ["bangalore"] * 4,
            "location": ["L1", "L2", "L3", "L4"],
            "cuisines": ["Italian", "Italian, Pizza", "Italian", "North Indian"],
            "cuisines_list": [["italian"], ["italian", "pizza"], ["italian"], ["north indian"]],
            "rating": [4.0, 4.2, 4.3, 4.1],
            "cost": [1200, 1100, 1300, 600],
            "budget_tier": ["Medium", "Medium", "Medium", "Low"],
            "popularity_score": [7.0, 8.0, 9.0, 6.0],
        })
        result = get_candidates(df, "bangalore", ["italian"], "Medium", 3.0)
        assert "Curry Den" not in result["name"].values

    def test_multiple_cuisines_any_match(self, sample_df):
        """Any cuisine match in the requested list should include the restaurant."""
        result = get_candidates(sample_df, "bangalore", ["italian", "north indian"], "Low", 3.0)
        names = result["name"].values
        assert "Pasta Palace" in names or "Curry House" in names

    def test_empty_cuisine_list_no_cuisine_filter(self, sample_df):
        """Empty cuisine list should not apply a cuisine filter."""
        result_all = get_candidates(sample_df, "bangalore", [], "Medium", 3.0)
        result_with_cuisine = get_candidates(sample_df, "bangalore", ["italian"], "Medium", 3.0)
        # With no cuisine filter, should return at least as many results
        assert len(result_all) >= len(result_with_cuisine)

    def test_cuisine_case_insensitive(self, sample_df):
        """Cuisine input should be matched case-insensitively."""
        lower = get_candidates(sample_df, "bangalore", ["italian"], "Medium", 3.0)
        upper = get_candidates(sample_df, "bangalore", ["ITALIAN"], "Medium", 3.0)
        assert set(lower["name"].values) == set(upper["name"].values)


class TestBudgetFilter:
    def test_exact_budget_match(self, sample_df):
        """Budget tier filter matches the selected tier."""
        result = get_candidates(sample_df, "bangalore", [], "Low", 3.0)
        names = result["name"].values
        # "Curry House" and "Burger Barn" are Low
        assert any(n in names for n in ["Curry House", "Burger Barn"])

    def test_budget_tier_tolerance_plus_one(self, sample_df):
        """±1 tier tolerance: 'Low' budget should also include 'Medium' restaurants."""
        result = get_candidates(sample_df, "bangalore", [], "Low", 3.0)
        tiers = result["budget_tier"].astype(str).unique()
        # Low ±1 → allows Low and Medium
        assert all(t in ("Low", "Medium") for t in tiers)

    def test_budget_tier_tolerance_medium(self, sample_df):
        """'Medium' ±1 tier allows Low, Medium, and High."""
        result = get_candidates(sample_df, "bangalore", [], "Medium", 3.0)
        tiers = result["budget_tier"].astype(str).unique()
        assert all(t in ("Low", "Medium", "High") for t in tiers)


class TestRatingFilter:
    def test_min_rating_applied(self):
        """All returned rows must have rating >= min_rating when strict pass yields >= 3 results."""
        df = pd.DataFrame({
            "name": ["High1", "High2", "High3", "Low1"],
            "city": ["bangalore"] * 4,
            "location": ["L1", "L2", "L3", "L4"],
            "cuisines": ["Italian"] * 4,
            "cuisines_list": [["italian"]] * 4,
            "rating": [4.5, 4.6, 4.7, 3.0],  # Low1 is below threshold
            "cost": [1000] * 4,
            "budget_tier": ["Medium"] * 4,
            "popularity_score": [7.0, 8.0, 9.0, 5.0],
        })
        result = get_candidates(df, "bangalore", [], "Medium", 4.4)
        assert not result.empty
        assert all(r >= 4.4 for r in result["rating"])

    def test_high_min_rating_excludes_low_rated(self):
        """Low-rated restaurant is excluded when strict pass has >= 3 qualifying rows."""
        df = pd.DataFrame({
            "name": ["Good1", "Good2", "Good3", "Burger Barn"],
            "city": ["bangalore"] * 4,
            "location": ["L1", "L2", "L3", "L4"],
            "cuisines": ["Indian"] * 4,
            "cuisines_list": [["indian"]] * 4,
            "rating": [4.5, 4.6, 4.7, 3.8],  # Burger Barn is below 4.3
            "cost": [500] * 4,
            "budget_tier": ["Low"] * 4,
            "popularity_score": [7.0, 8.0, 9.0, 5.0],
        })
        result = get_candidates(df, "bangalore", [], "Low", 4.3)
        assert "Burger Barn" not in result["name"].values


class TestSortAndTruncate:
    def test_sorted_by_popularity_desc(self, sample_df):
        result = get_candidates(sample_df, "bangalore", [], "Medium", 3.0)
        scores = result["popularity_score"].tolist()
        assert scores == sorted(scores, reverse=True)

    def test_max_results_respected(self, sample_df):
        result = get_candidates(sample_df, "bangalore", [], "Medium", 3.0, max_results=2)
        assert len(result) <= 2


# ─── 3.2 Fallback Chain Tests ────────────────────────────────────────────────

class TestFallbackChain:
    def test_fallback_pass1_relaxes_cuisine(self, sparse_df):
        """When strict results < MIN_STRICT_RESULTS, relax cuisine filter first."""
        # Request "Italian" in Mumbai — no Italian, but there are 2 restaurants
        # The strict result will be 0 (< 3), so fallback Pass 1 relaxes cuisine
        result = get_candidates(sparse_df, "mumbai", ["italian"], "Medium", 3.0)
        # Should return the 2 available restaurants after relaxing cuisine
        assert not result.empty

    def test_fallback_pass2_relaxes_budget(self):
        """When cuisine + budget give < 3, relax budget next."""
        df = pd.DataFrame({
            "name": ["R1", "R2", "R3"],
            "city": ["pune", "pune", "pune"],
            "location": ["L1", "L2", "L3"],
            "cuisines": ["Chinese", "Thai", "Mexican"],
            "cuisines_list": [["chinese"], ["thai"], ["mexican"]],
            "rating": [4.0, 4.1, 4.2],
            "cost": [2000, 2200, 2500],
            "budget_tier": ["High", "High", "High"],  # only High exists
            "popularity_score": [6.0, 7.0, 8.0],
        })
        # Request "Low" budget in Pune with "Chinese" — strict gives 0 results
        # Pass 1: relax cuisine → still all "High" → < 3 from Low ±1 perspective
        # Pass 2: relax budget → all 3 rows match city+rating → returns them
        result = get_candidates(df, "pune", ["chinese"], "Low", 3.0)
        assert not result.empty

    def test_fallback_pass3_city_only(self):
        """Last resort: return top-rated in city ignoring cuisine/budget/rating."""
        df = pd.DataFrame({
            "name": ["A", "B"],
            "city": ["agra", "agra"],
            "location": ["L1", "L2"],
            "cuisines": ["Mughlai", "Continental"],
            "cuisines_list": [["mughlai"], ["continental"]],
            "rating": [2.0, 2.5],   # both below any reasonable min_rating
            "cost": [3000, 4000],
            "budget_tier": ["High", "High"],
            "popularity_score": [3.0, 4.0],
        })
        # Even with strict min_rating=4.0 and "Low" budget, fallback Pass 3 kicks in
        result = get_candidates(df, "agra", ["pizza"], "Low", 4.0)
        assert not result.empty

    def test_strict_passes_when_enough_results(self, sample_df):
        """When strict filters return >= MIN_STRICT_RESULTS, no fallback is used."""
        # bangalore with Medium budget + no cuisine + low min_rating → many results
        result = get_candidates(sample_df, "bangalore", [], "Medium", 3.0)
        assert len(result) >= MIN_STRICT_RESULTS
        # All results should respect city
        assert all(r == "bangalore" for r in result["city"])


# ─── 3.3 Metadata Extractor Tests ───────────────────────────────────────────

class TestExtractMetadata:
    def test_returns_non_empty_cities(self, sample_df):
        meta = extract_metadata(sample_df)
        assert len(meta["cities"]) > 0

    def test_returns_non_empty_areas(self, sample_df):
        meta = extract_metadata(sample_df)
        assert "areas" in meta
        assert len(meta["areas"]) > 0
        assert "Indiranagar" in meta["areas"]

    def test_returns_non_empty_cuisines(self, sample_df):
        meta = extract_metadata(sample_df)
        assert len(meta["cuisines"]) > 0

    def test_cities_are_title_cased(self, sample_df):
        meta = extract_metadata(sample_df)
        assert "Bangalore" in meta["cities"]
        assert "Delhi" in meta["cities"]

    def test_cuisines_are_lowercase(self, sample_df):
        meta = extract_metadata(sample_df)
        assert "italian" in meta["cuisines"]
        assert "north indian" in meta["cuisines"]

    def test_budget_tiers_present(self, sample_df):
        meta = extract_metadata(sample_df)
        assert meta["budget_tiers"] == ["Low", "Medium", "High"]

    def test_rating_range_present(self, sample_df):
        meta = extract_metadata(sample_df)
        assert meta["rating_range"] == {"min": 1.0, "max": 5.0}

    def test_empty_df_returns_safe_defaults(self):
        meta = extract_metadata(pd.DataFrame())
        assert meta["cities"] == []
        assert meta["areas"] == []
        assert meta["cuisines"] == []
        assert meta["budget_tiers"] == ["Low", "Medium", "High"]


class TestAreaFilter:
    def test_area_filter_narrows_to_neighborhood(self, sample_df):
        res = get_candidates(sample_df, "bangalore", [], "Medium", 3.0, area="Indiranagar")
        assert not res.empty
        assert any(r.lower() == "indiranagar" for r in res["location"].astype(str))

    def test_area_filter_fallback_when_too_few(self, sample_df):
        # Even with niche area, fallback guarantees returning valid candidates
        res = get_candidates(sample_df, "bangalore", [], "Medium", 3.0, area="Whitefield")
        assert not res.empty
