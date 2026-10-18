"""API route definitions.

Phase 5 — REST Endpoints:
  GET  /api/health     → Liveness probe + dataset record count.
  GET  /api/metadata   → Available cities, cuisines, budget tiers for dropdowns.
  POST /api/recommend  → Main recommendation endpoint.
"""

from __future__ import annotations

import logging

import pandas as pd
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

from src.api.models import RecommendRequest, RecommendResponse, RestaurantCard
from src.config import settings
from src.engine.filter import extract_metadata, get_candidates
from src.engine.llm_recommender import get_recommendations
from src.engine.prompt_builder import build_prompt, sanitize_input

logger = logging.getLogger(__name__)
router = APIRouter()


def _get_df(request: Request) -> pd.DataFrame:
    """Safely retrieve the shared DataFrame from app state."""
    return getattr(request.app.state, "df", pd.DataFrame())


# ── GET /health ───────────────────────────────────────────────────────────────

@router.get(
    "/health",
    summary="Health check",
    description="Liveness probe. Returns HTTP 200 and the number of loaded restaurant records.",
    tags=["Ops"],
)
async def health(request: Request) -> dict:
    df = _get_df(request)
    return {"status": "ok", "records": len(df)}


# ── GET /metadata ─────────────────────────────────────────────────────────────

@router.get(
    "/metadata",
    summary="Filter options",
    description=(
        "Returns the full list of available cities, cuisine types, and budget tiers "
        "dynamically derived from the loaded dataset — used to populate frontend dropdowns."
    ),
    tags=["Recommendations"],
)
async def metadata(request: Request) -> dict:
    df = _get_df(request)
    return extract_metadata(df)


# ── POST /recommend ───────────────────────────────────────────────────────────

@router.post(
    "/recommend",
    response_model=RecommendResponse,
    summary="Get restaurant recommendations",
    description=(
        "Runs the full hybrid pipeline:\n"
        "1. **Filter** — narrows the full catalog to ≤15 candidates matching city, cuisine, budget, and rating.\n"
        "2. **LLM** — sends candidates to Groq LLM for ranked, personalised narration.\n"
        "3. **Guardrail** — removes any hallucinated restaurant names before returning.\n\n"
        "Falls back to heuristic ranking if the LLM is unavailable."
    ),
    tags=["Recommendations"],
)
async def recommend(payload: RecommendRequest, request: Request) -> RecommendResponse:
    df = _get_df(request)

    # ── Sanitize free-text context ────────────────────────────────────────────
    sanitized_context = sanitize_input(payload.context or "")
    req_dict = payload.model_dump()
    req_dict["context"] = sanitized_context

    logger.info(
        "Recommendation request — city=%s area=%s budget=%s cuisines=%s min_rating=%.1f",
        payload.location,
        payload.area,
        payload.budget.value,
        payload.cuisine,
        payload.min_rating,
    )

    # ── Candidate retrieval ───────────────────────────────────────────────────
    candidates = get_candidates(
        df=df,
        city=payload.location,
        cuisines=payload.cuisine,
        budget=payload.budget.value,
        min_rating=payload.min_rating,
        area=payload.area,
        max_results=min(payload.max_results + 2, settings.MAX_CANDIDATES),
    )

    if candidates.empty:
        logger.info("No candidates found for request — returning no_results.")
        return RecommendResponse(
            status="no_results",
            query_summary=(
                f"No restaurants matched your filters in {payload.location}. "
                "Try broadening your search."
            ),
            total_candidates_evaluated=0,
            recommendations=[],
            fallback_used=False,
        )

    logger.info("%d candidates retrieved — calling LLM.", len(candidates))

    # ── LLM narration ─────────────────────────────────────────────────────────
    prompt = build_prompt(candidates, req_dict)
    result = get_recommendations(prompt, candidates)

    # ── Coerce recommendations into RestaurantCard models ────────────────────
    # The LLM / heuristic may return dicts with minor type mismatches; be lenient.
    cards: list[RestaurantCard] = []
    for rec in result.get("recommendations", []):
        try:
            cards.append(RestaurantCard(**rec))
        except Exception as exc:
            logger.warning("Skipping malformed recommendation: %s — %s", rec.get("name"), exc)

    cards = cards[:payload.max_results]

    fallback_used: bool = result.get("fallback_used", False)
    logger.info(
        "Returning %d recommendations (fallback=%s).", len(cards), fallback_used
    )

    return RecommendResponse(
        status="success",
        query_summary=result.get("query_summary", "Here are your top matches."),
        total_candidates_evaluated=len(candidates),
        recommendations=cards,
        fallback_used=fallback_used,
    )
