"""Phase 5 API integration tests.

Tests use FastAPI's TestClient (ASGI in-process) with the real dataset loaded
via the lifespan handler. The LLM layer is always mocked so tests run offline
and deterministically.

Test groups:
  - TestHealthEndpoint    : GET /api/health
  - TestMetadataEndpoint  : GET /api/metadata
  - TestRecommendEndpoint : POST /api/recommend — valid payloads, edge cases
  - TestValidation        : Request contract violations (422 responses)
  - TestNoResults         : City with no matching restaurants
  - TestFallbackBanner    : fallback_used flag propagation
"""

from __future__ import annotations

from unittest.mock import patch

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from src.api.main import app

# ── Shared test client (loads real parquet via lifespan) ──────────────────────

@pytest.fixture(scope="module")
def client():
    """Start the app once for the whole module — dataset load is expensive."""
    with TestClient(app) as c:
        yield c


# ── Minimal in-memory DataFrame for isolated unit-style tests ─────────────────

@pytest.fixture(scope="module")
def mock_df():
    return pd.DataFrame({
        "name": ["Pasta Palace", "Curry House", "Sushi World", "Burger Barn", "Pizza Hut"],
        "city": ["bangalore"] * 5,
        "location": ["Indiranagar", "Koramangala", "BTM Layout", "HSR Layout", "MG Road"],
        "cuisines": ["Italian, Pasta", "North Indian", "Japanese", "American", "Italian, Pizza"],
        "cuisines_list": [
            ["italian", "pasta"],
            ["north indian"],
            ["japanese"],
            ["american"],
            ["italian", "pizza"],
        ],
        "rating": [4.5, 4.2, 4.8, 3.8, 4.3],
        "cost": [1200, 500, 2500, 400, 900],
        "budget_tier": ["Medium", "Low", "High", "Low", "Medium"],
        "popularity_score": [8.0, 6.0, 9.0, 5.0, 7.5],
    })


@pytest.fixture(scope="module")
def isolated_client(mock_df):
    """App client with the real dataset replaced by a tiny in-memory DataFrame."""
    with TestClient(app) as c:
        c.app.state.df = mock_df
        yield c


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/health
# ─────────────────────────────────────────────────────────────────────────────

class TestHealthEndpoint:
    def test_returns_200(self, client):
        r = client.get("/api/health")
        assert r.status_code == 200

    def test_status_ok(self, client):
        data = client.get("/api/health").json()
        assert data["status"] == "ok"

    def test_records_positive_with_real_data(self, client):
        """With the real parquet loaded, record count should be > 1000."""
        data = client.get("/api/health").json()
        assert data["records"] > 1000

    def test_records_key_present(self, client):
        data = client.get("/api/health").json()
        assert "records" in data


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/metadata
# ─────────────────────────────────────────────────────────────────────────────

class TestMetadataEndpoint:
    def test_returns_200(self, client):
        assert client.get("/api/metadata").status_code == 200

    def test_cities_non_empty(self, client):
        data = client.get("/api/metadata").json()
        assert len(data["cities"]) > 0

    def test_cuisines_non_empty(self, client):
        """cuisines_list column (numpy array) must be normalised to list on load."""
        data = client.get("/api/metadata").json()
        assert len(data["cuisines"]) > 0

    def test_budget_tiers_correct(self, client):
        data = client.get("/api/metadata").json()
        assert data["budget_tiers"] == ["Low", "Medium", "High"]

    def test_rating_range_present(self, client):
        data = client.get("/api/metadata").json()
        rr = data["rating_range"]
        assert rr["min"] == 1.0
        assert rr["max"] == 5.0

    def test_cities_title_cased(self, client):
        data = client.get("/api/metadata").json()
        for city in data["cities"]:
            assert city == city.title(), f"City not title-cased: {city}"

    def test_cuisines_are_lowercase(self, client):
        data = client.get("/api/metadata").json()
        for cuisine in data["cuisines"][:20]:      # spot-check first 20
            assert cuisine == cuisine.lower(), f"Cuisine not lowercase: {cuisine}"


# ─────────────────────────────────────────────────────────────────────────────
# POST /api/recommend — validation
# ─────────────────────────────────────────────────────────────────────────────

class TestValidation:
    def test_missing_location_returns_422(self, client):
        r = client.post("/api/recommend", json={"budget": "Medium"})
        assert r.status_code == 422

    def test_location_too_short_returns_422(self, client):
        r = client.post("/api/recommend", json={"location": "X", "budget": "Medium"})
        assert r.status_code == 422

    def test_invalid_budget_returns_422(self, client):
        r = client.post("/api/recommend", json={"location": "Bangalore", "budget": "Fancy"})
        assert r.status_code == 422

    def test_min_rating_out_of_range_returns_422(self, client):
        r = client.post("/api/recommend", json={
            "location": "Bangalore", "budget": "Medium", "min_rating": 6.0
        })
        assert r.status_code == 422

    def test_max_results_out_of_range_returns_422(self, client):
        r = client.post("/api/recommend", json={
            "location": "Bangalore", "budget": "Medium", "max_results": 0
        })
        assert r.status_code == 422

    def test_context_too_long_returns_422(self, client):
        r = client.post("/api/recommend", json={
            "location": "Bangalore", "budget": "Medium",
            "context": "A" * 301
        })
        assert r.status_code == 422


# ─────────────────────────────────────────────────────────────────────────────
# POST /api/recommend — happy paths (mocked LLM)
# ─────────────────────────────────────────────────────────────────────────────

_HEURISTIC_MOCK = {
    "query_summary": "Top matches for your search.",
    "recommendations": [
        {
            "rank": 1,
            "name": "Pasta Palace",
            "location": "Indiranagar",
            "cuisine": "Italian, Pasta",
            "rating": 4.5,
            "cost_for_two": "₹1200",
            "budget_tier": "Medium",
            "why_recommended": "Excellent Italian.",
            "highlights": ["Cozy", "Authentic"],
        }
    ],
    "fallback_used": False,
}

_FALLBACK_MOCK = {**_HEURISTIC_MOCK, "fallback_used": True,
                  "query_summary": "AI narration unavailable — showing top-rated matches."}


class TestRecommendEndpoint:
    def test_valid_request_returns_200(self, isolated_client):
        with patch("src.api.routes.get_recommendations", return_value=_HEURISTIC_MOCK):
            r = isolated_client.post("/api/recommend", json={
                "location": "Bangalore",
                "budget": "Medium",
                "cuisine": ["Italian"],
                "min_rating": 3.5,
                "max_results": 3,
            })
        assert r.status_code == 200

    def test_response_schema_fields(self, isolated_client):
        with patch("src.api.routes.get_recommendations", return_value=_HEURISTIC_MOCK):
            data = isolated_client.post("/api/recommend", json={
                "location": "Bangalore", "budget": "Medium",
            }).json()
        required = {"status", "query_summary", "total_candidates_evaluated",
                    "recommendations", "fallback_used"}
        assert required.issubset(data.keys())

    def test_status_success_when_results_found(self, isolated_client):
        with patch("src.api.routes.get_recommendations", return_value=_HEURISTIC_MOCK):
            data = isolated_client.post("/api/recommend", json={
                "location": "Bangalore", "budget": "Medium",
            }).json()
        assert data["status"] == "success"

    def test_recommendation_card_schema(self, isolated_client):
        with patch("src.api.routes.get_recommendations", return_value=_HEURISTIC_MOCK):
            data = isolated_client.post("/api/recommend", json={
                "location": "Bangalore", "budget": "Medium",
            }).json()
        rec = data["recommendations"][0]
        card_fields = {"rank", "name", "location", "cuisine", "rating",
                       "cost_for_two", "budget_tier", "why_recommended", "highlights"}
        assert card_fields.issubset(rec.keys())

    def test_max_results_respected(self, isolated_client):
        """API must not return more than max_results recommendations."""
        big_mock = {
            "query_summary": "Many results.",
            "recommendations": [
                {"rank": i + 1, "name": name, "location": "L", "cuisine": "Italian",
                 "rating": 4.0, "cost_for_two": "₹1000", "budget_tier": "Medium",
                 "why_recommended": "Good.", "highlights": []}
                for i, name in enumerate(["Pasta Palace", "Pizza Hut"])
            ],
            "fallback_used": False,
        }
        with patch("src.api.routes.get_recommendations", return_value=big_mock):
            data = isolated_client.post("/api/recommend", json={
                "location": "Bangalore", "budget": "Medium", "max_results": 2,
            }).json()
        assert len(data["recommendations"]) <= 2

    def test_fallback_used_false_when_llm_works(self, isolated_client):
        with patch("src.api.routes.get_recommendations", return_value=_HEURISTIC_MOCK):
            data = isolated_client.post("/api/recommend", json={
                "location": "Bangalore", "budget": "Medium",
            }).json()
        assert data["fallback_used"] is False

    def test_budget_case_sensitive_enum(self, isolated_client):
        """'medium' (lowercase) is not a valid BudgetTier — must be 'Medium'."""
        r = isolated_client.post("/api/recommend", json={
            "location": "Bangalore", "budget": "medium",
        })
        assert r.status_code == 422

    def test_no_cuisine_filter_returns_results(self, isolated_client):
        """Empty cuisine list should not block results."""
        with patch("src.api.routes.get_recommendations", return_value=_HEURISTIC_MOCK):
            data = isolated_client.post("/api/recommend", json={
                "location": "Bangalore", "budget": "Medium", "cuisine": [],
            }).json()
        assert data["status"] == "success"

    def test_context_is_sanitized(self, isolated_client):
        """Injection-style context must not cause a 500 — response should be 200."""
        with patch("src.api.routes.get_recommendations", return_value=_HEURISTIC_MOCK):
            r = isolated_client.post("/api/recommend", json={
                "location": "Bangalore", "budget": "Medium",
                "context": "<script>alert('xss')</script>",
            })
        assert r.status_code == 200

    def test_total_candidates_evaluated_positive(self, isolated_client):
        with patch("src.api.routes.get_recommendations", return_value=_HEURISTIC_MOCK):
            data = isolated_client.post("/api/recommend", json={
                "location": "Bangalore", "budget": "Medium",
            }).json()
        assert data["total_candidates_evaluated"] > 0


# ─────────────────────────────────────────────────────────────────────────────
# POST /api/recommend — no results
# ─────────────────────────────────────────────────────────────────────────────

class TestNoResults:
    def test_unknown_city_returns_no_results(self, isolated_client):
        r = isolated_client.post("/api/recommend", json={
            "location": "Atlantis", "budget": "Medium",
        })
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "no_results"
        assert data["recommendations"] == []
        assert data["total_candidates_evaluated"] == 0

    def test_no_results_fallback_used_is_false(self, isolated_client):
        """fallback_used should be False on a no_results response (no LLM was called)."""
        data = isolated_client.post("/api/recommend", json={
            "location": "Atlantis", "budget": "Medium",
        }).json()
        assert data["fallback_used"] is False


# ─────────────────────────────────────────────────────────────────────────────
# POST /api/recommend — fallback banner
# ─────────────────────────────────────────────────────────────────────────────

class TestFallbackBanner:
    def test_fallback_used_true_when_heuristic(self, isolated_client):
        """When LLM returns fallback_used=True, the API propagates it."""
        with patch("src.api.routes.get_recommendations", return_value=_FALLBACK_MOCK):
            data = isolated_client.post("/api/recommend", json={
                "location": "Bangalore", "budget": "Medium",
            }).json()
        assert data["fallback_used"] is True

    def test_fallback_summary_contains_ai_narration_unavailable(self, isolated_client):
        with patch("src.api.routes.get_recommendations", return_value=_FALLBACK_MOCK):
            data = isolated_client.post("/api/recommend", json={
                "location": "Bangalore", "budget": "Medium",
            }).json()
        assert "AI narration unavailable" in data["query_summary"]


# ─────────────────────────────────────────────────────────────────────────────
# Phase 6: Frontend UI Static File Serving
# ─────────────────────────────────────────────────────────────────────────────

class TestFrontendServing:
    def test_root_serves_index_html(self, client):
        """GET / should serve the frontend index.html."""
        response = client.get("/")
        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")
        assert "FoodTrail" in response.text
        assert "recommend-form" in response.text
        assert "area-select" in response.text

    def test_serves_styles_css(self, client):
        """GET /styles.css should serve CSS assets."""
        response = client.get("/styles.css")
        assert response.status_code == 200
        assert "text/css" in response.headers.get("content-type", "")

    def test_serves_app_js(self, client):
        """GET /app.js should serve client application logic."""
        response = client.get("/app.js")
        assert response.status_code == 200
        assert "application/javascript" in response.headers.get("content-type", "") or "text/javascript" in response.headers.get("content-type", "")


class TestAreaFiltering:
    def test_metadata_contains_areas(self, client):
        """GET /api/metadata includes areas list."""
        response = client.get("/api/metadata")
        assert response.status_code == 200
        data = response.json()
        assert "areas" in data
        assert isinstance(data["areas"], list)
        assert len(data["areas"]) > 0

    def test_recommend_with_specific_area(self, isolated_client):
        """POST /api/recommend works with optional area."""
        with patch("src.api.routes.get_recommendations", return_value=_HEURISTIC_MOCK):
            response = isolated_client.post("/api/recommend", json={
                "location": "Bangalore",
                "area": "Indiranagar",
                "budget": "Medium",
                "cuisine": [],
            })
            assert response.status_code == 200
            assert response.json()["status"] == "success"


