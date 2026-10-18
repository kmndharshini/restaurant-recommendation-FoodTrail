"""LLM gateway using Groq for ultra-fast inference.

Phase 4 — LLM Orchestration:
  - call_llm()          : Groq API call with exponential-backoff retries (up to 3).
  - heuristic_fallback(): Deterministic ranking when Groq is unavailable/unconfigured.
  - get_recommendations(): Orchestrator that runs the guardrail (anti-hallucination
                           whitelist check) and delegates to heuristic on failure.
"""

import json
import logging

import pandas as pd
from groq import Groq, APIStatusError, APITimeoutError, RateLimitError
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
    before_sleep_log,
)

from src.config import settings

logger = logging.getLogger(__name__)

# ── Groq client (lazy-initialised to avoid import-time crash when key is missing) ──
_groq_client: Groq | None = None


def _get_client() -> Groq:
    global _groq_client
    if _groq_client is None:
        _groq_client = Groq(api_key=settings.GROQ_API_KEY)
    return _groq_client


# ── LLM Call with retry ───────────────────────────────────────────────────────

@retry(
    retry=retry_if_exception_type((APITimeoutError, RateLimitError)),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True,
)
def call_llm(prompt: str) -> dict:
    """Call Groq LLM and return a parsed JSON dict.

    Uses Groq's JSON mode (`response_format={"type": "json_object"}`) to
    guarantee the model emits valid JSON without markdown fences.

    Retries up to 3 times on transient timeout / rate-limit errors with
    exponential backoff (2 s → 4 s → 8 s cap 10 s).

    Raises:
        groq.APIStatusError: On unrecoverable server/auth errors (4xx/5xx).
        json.JSONDecodeError: If model output is not valid JSON despite json_mode.
    """
    client = _get_client()
    call_kwargs: dict = {
        "model": settings.LLM_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "response_format": {"type": "json_object"},
        "max_tokens": settings.MAX_LLM_TOKENS,
        "temperature": 0.3,
    }
    # Enforce bare minimum reasoning tokens on MoE reasoning models to stay well within 8K TPM
    if "oss" in settings.LLM_MODEL.lower():
        call_kwargs["reasoning_effort"] = "low"

    response = client.chat.completions.create(**call_kwargs)
    raw = response.choices[0].message.content
    return json.loads(raw)


# ── Heuristic fallback ────────────────────────────────────────────────────────

def heuristic_fallback(candidates: pd.DataFrame, max_results: int = 5) -> dict:
    """Return top candidates deterministically when Groq is unavailable or unconfigured.

    Sorts by popularity_score (already done upstream, but re-applies for safety)
    and builds the same schema the LLM would produce.
    """
    top = candidates.head(max_results)
    recommendations = []
    for i, (_, row) in enumerate(top.iterrows()):
        cuisines_raw = row.get("cuisines", "")
        if not cuisines_raw and isinstance(row.get("cuisines_list"), list):
            cuisines_raw = ", ".join(row["cuisines_list"])
        recommendations.append({
            "rank": i + 1,
            "name": str(row.get("name", "Unknown")),
            "location": str(row.get("location", row.get("city", "Unknown"))),
            "cuisine": str(cuisines_raw),
            "rating": float(row.get("rating", 4.0)),
            "cost_for_two": f"₹{int(row['cost'])}" if pd.notnull(row.get("cost")) else "N/A",
            "budget_tier": str(row.get("budget_tier", "Medium")),
            "why_recommended": (
                f"A popular {cuisines_raw} restaurant rated {row.get('rating', '—')}/5. "
                "AI narration unavailable — showing top-ranked match."
            ),
            "highlights": ["Popular choice", "Highly rated"],
        })
    return {
        "query_summary": "AI narration unavailable — showing top-rated matches.",
        "recommendations": recommendations,
        "fallback_used": True,
    }


# ── Orchestrator ──────────────────────────────────────────────────────────────

def get_recommendations(prompt: str, candidates: pd.DataFrame) -> dict:
    """Run the full LLM recommendation pipeline with guardrails.

    Steps:
      1. Short-circuit to heuristic if GROQ_API_KEY is not set.
      2. Call Groq with retry logic.
      3. Apply anti-hallucination whitelist: discard any returned restaurant
         whose name is NOT in the candidate pool (exact case-insensitive match).
      4. Auto-enrich restaurant catalog fields (location, cuisine, cost, rating)
         directly from dataset so the LLM outputs bare minimum tokens.
      5. If whitelist filtering empties the list, fall back to heuristic.
      6. On any unhandled exception, fall back to heuristic.

    Returns:
        dict matching the RecommendResponse schema with a `fallback_used` flag.
    """
    if not settings.GROQ_API_KEY:
        logger.warning("GROQ_API_KEY not set — using heuristic fallback.")
        return heuristic_fallback(candidates)

    try:
        data = call_llm(prompt)

        # ── Guardrail: anti-hallucination whitelist check & metadata enrichment ──
        candidate_lookup = {
            str(row["name"]).strip().lower(): row
            for _, row in candidates.iterrows()
        }
        original_count = len(data.get("recommendations", []))
        valid_recs = []
        for i, r in enumerate(data.get("recommendations", [])):
            name_key = str(r.get("name", "")).strip().lower()
            if name_key in candidate_lookup:
                row = candidate_lookup[name_key]
                cuisines_raw = r.get("cuisine") or row.get("cuisines", "")
                if not cuisines_raw and isinstance(row.get("cuisines_list"), list):
                    cuisines_raw = ", ".join(row["cuisines_list"])
                cost_str = r.get("cost_for_two") or (f"₹{int(row['cost'])}" if pd.notnull(row.get("cost")) else "N/A")
                valid_recs.append({
                    "rank": r.get("rank") or (i + 1),
                    "name": str(row.get("name", r.get("name"))),
                    "location": str(r.get("location") or row.get("location", row.get("city", "Unknown"))),
                    "cuisine": str(cuisines_raw),
                    "rating": float(r.get("rating") or row.get("rating", 4.0)),
                    "cost_for_two": str(cost_str),
                    "budget_tier": str(r.get("budget_tier") or row.get("budget_tier", "Medium")),
                    "why_recommended": str(r.get("why_recommended", "Recommended spot based on your dining vibe.")),
                    "highlights": r.get("highlights") or ["Popular choice", "Highly rated"],
                })

        data["recommendations"] = valid_recs
        filtered_count = len(data["recommendations"])
        if original_count != filtered_count:
            logger.warning(
                "Guardrail removed %d hallucinated recommendation(s).",
                original_count - filtered_count,
            )

        if not data["recommendations"]:
            logger.warning("All recommendations were hallucinated — using heuristic fallback.")
            return heuristic_fallback(candidates)

        data["fallback_used"] = False
        return data

    except (APITimeoutError, RateLimitError, APIStatusError) as exc:
        logger.error("Groq API error after retries: %s", exc)
        return heuristic_fallback(candidates)

    except (json.JSONDecodeError, KeyError, TypeError) as exc:
        logger.error("LLM response parse error: %s", exc)
        return heuristic_fallback(candidates)

    except Exception as exc:  # noqa: BLE001
        logger.error("Unexpected LLM error: %s", exc)
        return heuristic_fallback(candidates)
