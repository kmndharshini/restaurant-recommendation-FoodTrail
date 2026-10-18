# 🚀 FoodTrail — Production Deployment Plan

This document outlines the step-by-step production deployment strategy for **FoodTrail** using a decoupled modern JAMstack architecture:
- **Backend**: FastAPI REST API + Zomato Dataset Engine deployed on **[Railway](https://railway.app)**.
- **Frontend**: Responsive Dark Mode AI Discovery Dashboard hosted on **[Vercel](https://vercel.com)**.

---

## 📑 Architecture Overview

```
┌────────────────────────────────────────────────────────┐
│                   Client Browser                       │
└───────────────────────────┬────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────┐
│               Vercel Edge Network (Frontend)           │
│   • Hosted from `src/ui/` (HTML5, Tailwind CDN, JS)    │
│   • Global CDN delivery & SSL                          │
│   • `vercel.json` Reverse Proxy (/api/* -> Railway)    │
└───────────────────────────┬────────────────────────────┘
                            │ (Transparent Proxy or Direct CORS)
                            ▼
┌────────────────────────────────────────────────────────┐
│             Railway Application (Backend)              │
│   • FastAPI + Uvicorn Worker Process                   │
│   • Loaded Zomato Parquet Catalog (9,229 records)      │
│   • Outbound HTTPS to Groq Cloud LLM API               │
│   • Liveness probe at `/api/health`                    │
└───────────────────────────┬────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────┐
│               Groq Cloud LLM Inference Engine          │
│   • LLaMA-3.3-70B / GPT-OSS-20B                        │
│   • Contextual reasoning & personalized narration      │
└───────────────────────────┘
```

---

## 📋 Prerequisites

1. **GitHub Repository**: All project code pushed to your GitHub account.
2. **Railway Account**: Sign up at [railway.app](https://railway.app).
3. **Vercel Account**: Sign up at [vercel.com](https://vercel.com).
4. **Groq Cloud API Key**: Active key from [console.groq.com](https://console.groq.com).

---

## 🛠️ Step 0: Repository Preparation

### 1. Commit the Processed Dataset (Recommended)
The preprocessed catalog [`data/processed/restaurants.parquet`](file:///d:/Restaurant%20Recommendation/data/processed/restaurants.parquet) is ~27.6 MB.
- GitHub allows file commits up to **100 MB** (and files < 50 MB have no restrictions).
- Committing this file ensures Railway starts up in **< 2 seconds** on cold boot without needing to download raw data from Hugging Face.

Update [`.gitignore`](file:///d:/Restaurant%20Recommendation/.gitignore):
```gitignore
# Keep data/raw ignored, but allow processed parquet catalog
data/raw/
!data/processed/restaurants.parquet
```

### 2. Create `Procfile` for Railway
Create a `Procfile` in the project root:
```text
web: uvicorn src.api.main:app --host 0.0.0.0 --port ${PORT:-8000}
```

### 3. Create `vercel.json` for Vercel
Create `vercel.json` in `src/ui/` (or repository root) to enable clean reverse proxying:
```json
{
  "rewrites": [
    {
      "source": "/api/:path*",
      "destination": "https://<YOUR-RAILWAY-SERVICE-URL>.up.railway.app/api/:path*"
    }
  ]
}
```

---

## 🚂 Part 1: Backend Deployment on Railway

### Step 1: Create New Project on Railway
1. Log in to [Railway](https://railway.app).
2. Click **"+ New Project"** → Select **"Deploy from GitHub repo"**.
3. Choose your `Restaurant Recommendation` repository.
4. Click **"Deploy Now"**.

### Step 2: Configure Service Settings
1. In the Railway project dashboard, select your deployed service.
2. Go to the **"Settings"** tab:
   - **Service Name**: Rename to `foodtrail-backend` (or your preferred name).
   - **Build Command**: Leave default (Railway automatically detects Python via `requirements.txt`).
   - **Start Command**: 
     ```bash
     uvicorn src.api.main:app --host 0.0.0.0 --port $PORT
     ```
   - **Healthcheck Path**: `/api/health`
   - **Healthcheck Timeout**: `120` seconds (allows dataset loading into memory on boot).

### Step 3: Configure Environment Variables
Navigate to the **"Variables"** tab and add the following:

| Variable Name | Value | Purpose |
|---|---|---|
| `GROQ_API_KEY` | `gsk_your_actual_groq_api_key` | Groq Cloud LLM access token |
| `LLM_PROVIDER` | `groq` | Inference provider backend |
| `LLM_MODEL` | `openai/gpt-oss-20b` | Target Groq model |
| `MAX_CANDIDATES` | `15` | Max candidate pool for prompt |
| `MAX_LLM_TOKENS` | `800` | Token limit for JSON narration |
| `PYTHONUNBUFFERED` | `1` | Real-time console logs |

*(Note: `PORT` is automatically injected by Railway — do not manually define it).*

### Step 4: Generate a Public Domain
1. In the **Settings** tab, scroll to **"Networking"**.
2. Click **"Generate Domain"**.
3. Railway will assign a public HTTPS URL (e.g. `https://foodtrail-backend-production.up.railway.app`).
4. **Copy this URL** for the next step.

### Step 5: Verify Backend Deployment
Test the live endpoints using `curl` or your browser:
```bash
# 1. Health Probe
curl https://<YOUR-RAILWAY-URL>.up.railway.app/api/health
# Expected: {"status":"ok","records":9229}

# 2. Metadata Catalog
curl https://<YOUR-RAILWAY-URL>.up.railway.app/api/metadata
# Expected: JSON with cities and cuisines list

# 3. Interactive Documentation
Open https://<YOUR-RAILWAY-URL>.up.railway.app/docs in browser
```

---

## ⚡ Part 2: Frontend Deployment on Vercel

The frontend is a static single-page application located in [`src/ui/`](file:///d:/Restaurant%20Recommendation/src/ui/).

### Step 1: Configure `vercel.json`
Update `src/ui/vercel.json` with your actual Railway backend URL from Part 1:
```json
{
  "cleanUrls": true,
  "rewrites": [
    {
      "source": "/api/:path*",
      "destination": "https://foodtrail-backend-production.up.railway.app/api/:path*"
    }
  ],
  "headers": [
    {
      "source": "/(.*)",
      "headers": [
        { "key": "X-Frame-Options", "value": "DENY" },
        { "key": "X-Content-Type-Options", "value": "nosniff" },
        { "key": "Referrer-Policy", "value": "strict-origin-when-cross-origin" }
      ]
    }
  ]
}
```

### Step 2: Import Project into Vercel
1. Log in to [Vercel](https://vercel.com).
2. Click **"Add New..."** → **"Project"**.
3. Select your GitHub repository.
4. In the **Configure Project** screen:
   - **Project Name**: `foodtrail-ai` (or your choice).
   - **Framework Preset**: Select **"Other"**.
   - **Root Directory**: Click *Edit* and select **`src/ui`**.
   - **Build and Output Settings**: Leave defaults (no build command needed for pure HTML/CSS/JS).
5. Click **"Deploy"**.

### Step 3: Verify Frontend Deployment
1. Vercel will deploy in ~15 seconds and assign a URL (e.g., `https://foodtrail-ai.vercel.app`).
2. Open the URL in your browser:
   - Verify the top status badge shows **"Dataset Ready • 9,229 Venues"**.
   - Verify the City and Area dropdowns populate with Bangalore neighborhoods.
   - Click **"Find Restaurants with AI"** and verify live cards appear with Groq narration.
   - Click a card to confirm the **Deep Dive AI Dossier** modal opens smoothly.

---

## 🔒 Part 3: CORS & Security Configuration

The FastAPI backend is pre-configured with permissive CORS in [`src/api/main.py`](file:///d:/Restaurant%20Recommendation/src/api/main.py#L106-L112):
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### Production Hardening (Optional Best Practice)
To restrict API access strictly to your Vercel deployment:
1. Update `main.py`:
   ```python
   ALLOWED_ORIGINS = [
       "https://foodtrail-ai.vercel.app",
       "http://localhost:8000",
       "http://127.0.0.1:8000",
   ]
   app.add_middleware(
       CORSMiddleware,
       allow_origins=ALLOWED_ORIGINS,
       allow_credentials=True,
       allow_methods=["*"],
       allow_headers=["*"],
   )
   ```
2. Commit and push to GitHub. Railway will automatically redeploy.

---

## 🔄 Part 4: CI/CD & Automated Updates

Both Railway and Vercel support native GitHub webhook integration:
- **Pushing changes to `main`**:
  - Code changes in `src/api/` or `src/engine/` automatically trigger a **Railway build & zero-downtime redeploy**.
  - UI changes in `src/ui/` automatically trigger a **Vercel atomic deployment** within seconds.

---

## 🛠️ Troubleshooting & Common Pitfalls

| Issue | Cause | Solution |
|---|---|---|
| **Railway Deploy Times Out / Exceeds Memory** | Railway is downloading raw CSV from Hugging Face on cold start | Commit `data/processed/restaurants.parquet` to Git directly, or increase Healthcheck timeout to 180s. |
| **API Returns 404 on Vercel** | `vercel.json` rewrites not configured or wrong destination URL | Ensure `src/ui/vercel.json` points to your exact Railway URL with `/api/:path*`. |
| **CORS Errors in Browser Console** | Calling Railway directly without proxy or missing CORS headers | Use the Vercel rewrite proxy (`/api/...`) or ensure `CORSMiddleware` in `main.py` allows your Vercel domain. |
| **Groq 401 Unauthorized** | Missing or incorrect `GROQ_API_KEY` | Check Railway **Variables** tab and ensure the key starts with `gsk_`. |
| **Railway Crashes on Port Binding** | Server tried to bind to `127.0.0.1` instead of `0.0.0.0` | Ensure the start command uses `--host 0.0.0.0 --port $PORT`. |

---

## 📊 Post-Deployment Verification Checklist

- [ ] Railway service shows **"Active"** status with green indicator.
- [ ] `GET /api/health` returns `HTTP 200` with 9,229 loaded records.
- [ ] Vercel static deployment resolves with custom fonts and ambient glow.
- [ ] City and Area dropdowns populate from live metadata.
- [ ] Recommendation request successfully reaches Groq and returns ranked cards.
- [ ] Deep Dive modal displays review sentiment distribution and citations.
- [ ] Shortlist bookmarks save and persist across page reloads.
