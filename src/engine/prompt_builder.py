"""Prompt construction and input sanitization for Groq inference.

Phase 4 — Prompt Engineering:
  - SYSTEM_PROMPT  : Grounding rules + persona for the food concierge.
  - sanitize_input(): Strip injection-style characters from free-text input.
  - build_prompt() : Assemble the full user+candidate context into a single prompt.

Design Notes:
  - Groq models follow JSON mode reliably when the schema is
    embedded directly in the prompt (no markdown fences needed).
  - The schema is always injected at the end so the model can "see" the
    target structure just before it starts generating.
"""

import json
import re
import pandas as pd

# ── System Prompt ─────────────────────────────────────────────────────────────

# ── System Prompt ─────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """\
You are an expert food concierge. Recommend best matching restaurants from CANDIDATES.
RULES:
1. ONLY recommend restaurants from the CANDIDATE LIST.
2. Return a valid JSON object matching the schema.
3. Keep descriptions brief: 1 concise sentence for why_recommended, 2 short highlights.
"""

# ── Input Sanitizer ───────────────────────────────────────────────────────────

def sanitize_input(text: str, max_length: int = 300) -> str:
    """Strip control characters and limit length to prevent prompt injection.

    Allows alphanumerics, spaces, and safe punctuation (,.!?'\"₹-).
    Truncates to max_length characters after stripping.
    """
    if not text:
        return ""
    text = re.sub(r"[^\w\s,.!?'\"₹-]", "", text)
    return text[:max_length].strip()


# ── Prompt Builder ────────────────────────────────────────────────────────────

def build_prompt(candidates: pd.DataFrame, user_request: dict) -> str:
    """Assemble a grounded LLM prompt from the filtered candidate pool and user intent.

    Args:
        candidates: DataFrame returned by get_candidates() — already filtered & ranked.
        user_request: Dict matching RecommendRequest fields
                      (location, cuisine, budget, min_rating, context, max_results).

    Returns:
        A complete prompt string ready to be sent to Groq.
    """
    # ── Format candidate list (compact token format) ──────────────────────────
    candidate_lines: list[str] = []
    for _, row in candidates.iterrows():
        name      = row.get("name", "Unknown")
        loc       = row.get("location", row.get("city", "Unknown"))
        cuisines  = row.get("cuisines") or ", ".join(row.get("cuisines_list") or [])
        rating    = row.get("rating", "N/A")
        cost      = int(row["cost"]) if pd.notnull(row.get("cost")) else "N/A"
        score     = round(float(row.get("popularity_score", 0)), 2)
        candidate_lines.append(
            f"- {name} | {loc} | {cuisines} | Rating: {rating}/5 | Cost: ₹{cost} | Popularity Score: {score}"
        )
    candidates_text = "\n".join(candidate_lines)

    # ── Format user context ───────────────────────────────────────────────────
    cuisine_str = ", ".join(user_request.get("cuisine") or ["Any"])
    context_str = sanitize_input(user_request.get("context") or "General dining")
    area_str = f"Area: {user_request.get('area')}\n" if user_request.get("area") else ""
    user_context = (
        f"City: {user_request.get('location', '')}\n"
        f"{area_str}"
        f"Cuisine Preference: {cuisine_str}\n"
        f"Budget Tier: {user_request.get('budget', 'Medium')}\n"
        f"Minimum Rating: {user_request.get('min_rating', 3.5)}/5\n"
        f"Max Results Requested: {user_request.get('max_results', 5)}\n"
        f"Occasion / Context: {context_str}"
    )

    # ── Output schema (bare minimum token structure) ──────────────────────────
    example_rec = {
        "name": "<Exact candidate name>",
        "why_recommended": "<1 concise sentence>",
        "highlights": ["<tag1>", "<tag2>"],
    }
    output_schema = json.dumps(
        {
            "query_summary": "<1-sentence summary>",
            "recommendations": [example_rec],
        },
        indent=1,
        ensure_ascii=False,
    )

    return (
        f"{SYSTEM_PROMPT}\n"
        f"USER REQUEST:\n{user_context}\n\n"
        f"CANDIDATE LIST:\n{candidates_text}\n\n"
        f"OUTPUT (JSON only):\n{output_schema}"
    )
