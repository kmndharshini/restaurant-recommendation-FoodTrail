"""FastAPI application entry point.

Phase 5 — Application bootstrap:
  - Lifespan handler   : Loads (or builds) the processed dataset on startup.
  - CORS middleware    : Allows all origins so the UI can call the API from any host.
  - Router mounting    : All API routes under the /api prefix.
  - Static file mount  : Serves the frontend UI from src/ui/.
  - Logging config     : Structured console logging for visibility.
"""

from __future__ import annotations

import logging
import os

import pandas as pd
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from src.api.routes import router
from src.config import settings

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


# ── Dataset loader ─────────────────────────────────────────────────────────────

def _load_or_build_dataset() -> pd.DataFrame:
    """Return the processed DataFrame, building it from scratch if needed."""
    if os.path.exists(settings.PROCESSED_DATA_PATH):
        logger.info("Loading processed dataset from %s", settings.PROCESSED_DATA_PATH)
        df = pd.read_parquet(settings.PROCESSED_DATA_PATH)

        # Normalise cuisines_list: parquet may store lists as numpy arrays.
        # Ensure every cell is a plain Python list of lowercase strings.
        if "cuisines_list" in df.columns:
            df["cuisines_list"] = df["cuisines_list"].apply(
                lambda x: [str(c).strip().lower() for c in x]
                if hasattr(x, "__iter__") and not isinstance(x, str)
                else []
            )

        logger.info("Dataset ready — %d restaurants loaded.", len(df))
        return df

    # ── Build from raw data ───────────────────────────────────────────────────
    logger.warning(
        "Processed dataset not found at %s — running pipeline now.",
        settings.PROCESSED_DATA_PATH,
    )
    try:
        from src.data.ingest import ingest_dataset
        from src.data.preprocess import preprocess, save_processed

        raw_df = ingest_dataset(settings.DATASET_ID)
        processed_df = preprocess(raw_df)
        os.makedirs(os.path.dirname(settings.PROCESSED_DATA_PATH), exist_ok=True)
        save_processed(processed_df, settings.PROCESSED_DATA_PATH)
        logger.info("Pipeline complete — %d restaurants saved.", len(processed_df))
        return processed_df
    except Exception as exc:
        logger.error("Pipeline failed: %s — starting with empty dataset.", exc)
        return pd.DataFrame(
            columns=[
                "name", "city", "location", "cuisines", "cuisines_list",
                "rating", "cost", "budget_tier", "popularity_score",
            ]
        )


# ── Lifespan ──────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load dataset on startup; release resources on shutdown."""
    app.state.df = _load_or_build_dataset()
    yield
    logger.info("Server shutting down.")


# ── Application ───────────────────────────────────────────────────────────────

app = FastAPI(
    title="FoodTrail — AI Restaurant Recommendation API",
    description=(
        "Hybrid LLM-powered restaurant discovery engine built on the Zomato dataset. "
        "Combines deterministic candidate filtering (Phase 3) with Groq LLM narration "
        "(Phase 4) to surface personalised, explainable recommendations.\n\n"
        "**Quick start**: `POST /api/recommend` with a city, optional area, budget, and cuisine preferences."
    ),
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── CORS ──────────────────────────────────────────────────────────────────────
raw_origins = getattr(settings, "ALLOWED_ORIGINS", "*")
if raw_origins == "*":
    cors_origins = ["*"]
else:
    cors_origins = [o.strip() for o in raw_origins.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins if cors_origins else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routes ────────────────────────────────────────────────────────────────────
app.include_router(router, prefix="/api", tags=["Recommendations"])

# ── Static UI ─────────────────────────────────────────────────────────────────
_ui_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "ui")
if os.path.isdir(_ui_dir):
    app.mount("/", StaticFiles(directory=_ui_dir, html=True), name="ui")
    logger.info("UI served from %s", _ui_dir)
