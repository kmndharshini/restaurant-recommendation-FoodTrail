# 🧭 FoodTrail — AI-Powered Restaurant Recommendation System

[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110%2B-009688.svg)](https://fastapi.tiangolo.com)
[![Groq Cloud](https://img.shields.io/badge/LLM-Groq%20Cloud-orange.svg)](https://groq.com)
[![Tests Passing](https://img.shields.io/badge/tests-96%20passed-brightgreen.svg)](#running-tests)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

An intelligent, hybrid restaurant recommendation engine inspired by Zomato. Combines **deterministic multi-tier structured filtering** (city, neighborhood area, optional cuisine, budget tier, and minimum rating) with **Large Language Model (Groq Cloud) contextual reasoning** and personalised natural-language explanations.

---

## 📑 Table of Contents

- [Project Overview](#project-overview)
- [System Architecture](#system-architecture)
- [Features](#features)
- [Quick Start](#quick-start)
- [Environment Variables](#environment-variables)
- [API Reference](#api-reference)
- [Dataset Source](#dataset-source)
- [Running Tests](#running-tests)
- [Project Structure](#project-structure)

---

## 🌟 Project Overview

Traditional recommendation systems suffer from two extremes:
1. **Pure keyword / SQL filters** that return robotic lists without contextual empathy or vibe understanding.
2. **Pure LLM chat bots** that hallucinate non-existent restaurants, fabricate pricing, and ignore actual catalog constraints.

**FoodTrail** solves this through a **two-stage hybrid architecture**:
* **Stage 1 (Deterministic Candidate Retrieval)**: Narrows down 9,200+ raw restaurant records into ≤15 high-quality candidates using strict filtering across city, neighborhood area, optional cuisine, budget, and rating, with automatic fallback relaxation.
* **Stage 2 (Grounded LLM Orchestration)**: Uses Groq's high-speed inference engine (`openai/gpt-oss-20b`) to rank candidates and generate personalized "Why You'll Love This" dining insights.
* **Stage 3 (Anti-Hallucination Guardrail)**: Whitelist-filters all LLM outputs against the actual candidate pool, guaranteeing 100% grounded results.

---

## 🏗️ System Architecture

```
┌────────────────────────────────────────────────────────┐
│                   Web Browser UI                       │
│    (HTML5 · CSS3 Modern Dark Mode · Vanilla JS)        │
└───────────────────────────┬────────────────────────────┘
                            │ POST /api/recommend
                            ▼
┌────────────────────────────────────────────────────────┐
│                 FastAPI Backend Service                │
├────────────────────────────────────────────────────────┤
│ 1. Candidate Filter (filter.py)                        │
│    • City match (case-insensitive)                     │
│    • Cuisine overlap (multi-select)                    │
│    • Budget tier (±1 tier tolerance fallback)          │
│    • Min rating filter & Popularity ranking            │
├────────────────────────────────────────────────────────┤
│ 2. Prompt Builder (prompt_builder.py)                  │
│    • Input sanitization (injection prevention)         │
│    • Grounded system prompt with JSON schema           │
├────────────────────────────────────────────────────────┤
│ 3. Groq LLM Gateway (llm_recommender.py)               │
│    • Native JSON mode (`response_format`)              │
│    • Exponential backoff retries (Tenacity)            │
│    • Anti-hallucination whitelist guardrail            │
│    • Heuristic fallback (zero downtime guarantee)      │
└────────────────────────────────────────────────────────┘
```

For complete technical diagrams and architectural deep-dives, see [`docs/architecture.md`](docs/architecture.md).

---

## ✨ Features

- **Rich Modern UI**: Responsive dark mode with glassmorphic cards, Google Fonts (`Outfit` & `Plus Jakarta Sans`), smooth micro-animations, and live range sliders.
- **Dynamic Metadata Integration**: Cities and cuisines dynamically populated from `/api/metadata` using actual dataset values.
- **Contextual Reasoning**: Understands user intent like *"romantic candle-light date"* or *"quiet cafe to work with good coffee"*.
- **Anti-Hallucination Guardrails**: Cross-references every LLM recommendation with candidate names; discards ungrounded entries.
- **Graceful Fallbacks**: If API quotas or network limits occur, the system automatically falls back to deterministic heuristic ranking with a clear status banner.
- **Interactive Documentation**: Auto-generated Swagger UI and OpenAPI specifications.

---

## 🚀 Quick Start

### 1. Prerequisites
- Python 3.10, 3.11, or 3.12
- Free Groq Cloud API key from [https://console.groq.com](https://console.groq.com)

### 2. Clone and Setup Environment

```bash
# Clone the repository
git clone <repo-url>
cd "Restaurant Recommendation"

# Create and activate virtual environment
# On Windows:
python -m venv .venv
.venv\Scripts\activate

# On macOS / Linux:
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Configure Environment Variables

Copy `.env.example` to `.env` and insert your Groq API key:

```bash
cp .env.example .env
```

Open `.env` and set:
```ini
GROQ_API_KEY=gsk_your_actual_groq_api_key_here
LLM_PROVIDER=groq
LLM_MODEL=openai/gpt-oss-20b
```

### 4. Run the Application Server

```bash
uvicorn src.api.main:app --reload --port 8000
```

- **Web Application**: Open [http://localhost:8000](http://localhost:8000) in your browser.
- **Interactive Swagger Docs**: Open [http://localhost:8000/docs](http://localhost:8000/docs).
- **Alternative ReDoc**: Open [http://localhost:8000/redoc](http://localhost:8000/redoc).

---

## ⚙️ Environment Variables

| Variable | Type | Default | Description |
|---|---|---|---|
| `GROQ_API_KEY` | `str` | `""` | Groq Cloud API key (required for AI narration) |
| `LLM_PROVIDER` | `str` | `"groq"` | LLM provider backend (`groq`) |
| `LLM_MODEL` | `str` | `"openai/gpt-oss-20b"` | Groq-hosted model ID |
| `MAX_CANDIDATES` | `int` | `15` | Maximum candidate pool passed to prompt |
| `MAX_LLM_TOKENS` | `int` | `800` | Max tokens generated per recommendation call |
| `DATASET_ID` | `str` | `ManikaSaini/zomato-restaurant-recommendation` | Hugging Face dataset identifier |
| `PROCESSED_DATA_PATH` | `str` | `data/processed/restaurants.parquet` | Local path to preprocessed Parquet catalog |

---

## 📡 API Reference

### 1. Health Probe
```http
GET /api/health
```
**Response (200 OK)**:
```json
{
  "status": "ok",
  "records": 9229
}
```

### 2. Filter Metadata
```http
GET /api/metadata
```
**Response (200 OK)**:
```json
{
  "cities": ["Bangalore"],
  "cuisines": ["american", "bakery", "beverages", "biryani", "cafe", "chinese", "continental", "desserts", "fast food", "italian", "north indian", "pizza", "south indian"],
  "budget_tiers": ["Low", "Medium", "High"],
  "rating_range": { "min": 1.0, "max": 5.0 }
}
```

### 3. Get Recommendations
```http
POST /api/recommend
Content-Type: application/json
```

**Request Body**:
```json
{
  "location": "Bangalore",
  "budget": "Medium",
  "cuisine": ["Italian"],
  "min_rating": 4.0,
  "context": "Romantic anniversary dinner with pasta",
  "max_results": 3
}
```

**Response (200 OK)**:
```json
{
  "status": "success",
  "query_summary": "Top Italian spots in Bangalore for a romantic dinner",
  "total_candidates_evaluated": 15,
  "recommendations": [
    {
      "rank": 1,
      "name": "Chianti",
      "location": "Koramangala 5th Block",
      "cuisine": "Italian, Pizza",
      "rating": 4.5,
      "cost_for_two": "₹1500",
      "budget_tier": "Medium",
      "why_recommended": "Renowned for authentic hand-crafted pasta and intimate candlelit wine dining ideal for celebrations.",
      "highlights": ["Handmade Pasta", "Romantic Ambience", "Wine Selection"]
    }
  ],
  "fallback_used": false
}
```

---

## 📊 Dataset Source

- **Dataset**: `ManikaSaini/zomato-restaurant-recommendation`
- **Hosted On**: [Hugging Face Datasets](https://huggingface.co/datasets/ManikaSaini/zomato-restaurant-recommendation)
- **Catalog Size**: 9,229 cleaned restaurant records across Bangalore
- **Processed Format**: Apache Parquet with snappy compression (`data/processed/restaurants.parquet`)

---

## 🧪 Running Tests

The test suite covers data pipelines, candidate retrieval, prompt injection defense, LLM guardrails, FastAPI routes, and static UI file serving:

```bash
# Run all tests with verbosity
pytest tests/ -v

# Run with test coverage report
pytest --cov=src tests/
```

---

## 📁 Project Structure

```
Restaurant Recommendation/
├── data/
│   ├── raw/                      # Downloaded source files
│   └── processed/
│       └── restaurants.parquet   # 9.2k preprocessed records
├── docs/
│   ├── architecture.md           # System architecture & sequence flows
│   ├── implementation-plan.md    # 6-phase project implementation roadmap
│   ├── problemStatement.md       # Requirements & functional scope
│   ├── edge-case.md              # Corner cases & resilience handling
│   └── eval.md                   # Evaluation rubrics & benchmarks
├── src/
│   ├── api/
│   │   ├── main.py               # FastAPI app & static UI mounting
│   │   ├── models.py             # Pydantic request/response schemas
│   │   └── routes.py             # REST API routes (/health, /metadata, /recommend)
│   ├── data/
│   │   ├── ingest.py             # Hugging Face dataset download
│   │   └── preprocess.py         # Cleaning, normalization & tier assignment
│   ├── engine/
│   │   ├── filter.py             # Deterministic filtering & fallback relaxation
│   │   ├── prompt_builder.py     # Prompt assembly & input sanitization
│   │   └── llm_recommender.py    # Groq API client, retries & guardrails
│   ├── ui/
│   │   ├── index.html            # Semantic, responsive UI layout
│   │   ├── styles.css            # Dark mode, glassmorphism & animations
│   │   └── app.js                # Dynamic filters, metadata fetch & card rendering
│   └── config.py                 # Pydantic Settings configuration
├── tests/
│   ├── test_data_pipeline.py     # ETL tests
│   ├── test_filter.py            # Filtering & fallback tests
│   ├── test_llm_orchestration.py # Prompt builder & guardrail tests
│   └── test_api.py               # FastAPI endpoint & UI serving tests
├── .env.example                  # Environment template
├── requirements.txt              # Production & test dependencies
└── README.md                     # Comprehensive project documentation
```

---

## 📜 License

This project is licensed under the MIT License.
