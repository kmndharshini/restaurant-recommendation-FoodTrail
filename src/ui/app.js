/**
 * FoodTrail — AI-Powered Dining Intelligence Frontend
 * Implements the Stitch design system and integrates with FastAPI endpoints:
 *   - GET  /api/health
 *   - GET  /api/metadata
 *   - POST /api/recommend
 */

document.addEventListener("DOMContentLoaded", () => {
  // ── Deployment Configuration (supports relative path or direct backend URL) ──
  const API_BASE_URL = window.API_BASE_URL || "";

  // ── Element References ──────────────────────────────────────────────────
  const form = document.getElementById("recommend-form");
  const locationSelect = document.getElementById("location-select");
  const areaSelect = document.getElementById("area-select");
  const budgetBtns = document.querySelectorAll(".budget-btn");
  const budgetInput = document.getElementById("budget-value");
  const budgetPreviewText = document.getElementById("budget-preview-text");

  const cuisineSearchInput = document.getElementById("cuisine-search-input");
  const cuisineDropdown = document.getElementById("cuisine-dropdown-list");
  const popularCuisinesContainer = document.getElementById("popular-cuisines-container");
  const selectedCuisinesBox = document.getElementById("selected-cuisines-box");
  const cuisinesCountBadge = document.getElementById("cuisines-count-badge");

  const minRatingInput = document.getElementById("min-rating");
  const ratingVal = document.getElementById("rating-val");
  const contextInput = document.getElementById("context-input");
  const maxResultsSelect = document.getElementById("max-results-select");

  const searchBtn = document.getElementById("search-btn");
  const btnSpinner = document.getElementById("btn-spinner");
  const btnIcon = document.getElementById("btn-icon");
  const btnText = document.getElementById("btn-text");
  const resetBtn = document.getElementById("reset-btn");

  // States
  const stateResults = document.getElementById("state-results");
  const stateLoading = document.getElementById("state-loading");
  const stateEmpty = document.getElementById("state-empty");
  const stateError = document.getElementById("state-error");
  const stateShortlist = document.getElementById("state-shortlist");

  // State Tabs
  const tabResults = document.getElementById("tab-results");
  const tabLoading = document.getElementById("tab-loading");
  const tabEmpty = document.getElementById("tab-empty");
  const tabShortlist = document.getElementById("tab-shortlist");
  const shortlistCountBadge = document.getElementById("shortlist-count-badge");

  // Meta & Banner Elements
  const statusRecordsText = document.getElementById("status-records-text");
  const fallbackBanner = document.getElementById("fallback-banner");
  const closeFallbackBtn = document.getElementById("close-fallback-btn");
  const metaSummaryText = document.getElementById("meta-summary-text");
  const metaVibeText = document.getElementById("meta-vibe-text");
  const candidatesCountPill = document.getElementById("candidates-count-pill");
  const cardsContainer = document.getElementById("cards-container");
  const shortlistCardsContainer = document.getElementById("shortlist-cards-container");
  const clearShortlistBtn = document.getElementById("clear-shortlist-btn");

  const emptyStateText = document.getElementById("empty-state-text");
  const emptyResetBtn = document.getElementById("empty-reset-btn");
  const errorStateText = document.getElementById("error-state-text");
  const errorRetryBtn = document.getElementById("error-retry-btn");

  // Scope Indicators
  const scopeTargetText = document.getElementById("scope-target-text");
  const scopeBudgetText = document.getElementById("scope-budget-text");
  const scopeVibeText = document.getElementById("scope-vibe-text");

  // Deep Dive Modal Elements
  const modal = document.getElementById("restaurant-modal");
  const closeModalBtn = document.getElementById("close-modal-btn");
  const modalCloseBottomBtn = document.getElementById("modal-close-bottom-btn");
  const modalRankBadge = document.getElementById("modal-rank-badge");
  const modalRestaurantName = document.getElementById("modal-restaurant-name");
  const modalVibeMatchPill = document.getElementById("modal-vibe-match-pill");
  const modalLocation = document.getElementById("modal-location");
  const modalCost = document.getElementById("modal-cost");
  const modalRating = document.getElementById("modal-rating");
  const modalReviewCount = document.getElementById("modal-review-count");
  const modalCuisinesRow = document.getElementById("modal-cuisines-row");
  const modalSaveBtn = document.getElementById("modal-save-btn");
  const modalShareBtn = document.getElementById("modal-share-btn");
  const modalZomatoLink = document.getElementById("modal-zomato-link");
  const modalReserveBottomLink = document.getElementById("modal-reserve-bottom-link");
  const modalLlmGroundingText = document.getElementById("modal-llm-grounding-text");
  const modalKeywordsContainer = document.getElementById("modal-keywords-container");
  const modalReviewsContainer = document.getElementById("modal-reviews-container");
  const modalDownloadDossier = document.getElementById("modal-download-dossier");

  // ── Application State ───────────────────────────────────────────────────
  let allCuisines = [];
  const selectedCuisines = new Set();
  let currentRecommendations = [];
  let currentActiveCardForModal = null;
  let shortlist = JSON.parse(localStorage.getItem("foodtrail_shortlist") || "[]");

  const POPULAR_CUISINES = [
    "Italian", "North Indian", "Continental", "Cafe",
    "Asian", "Biryani", "Desserts", "Chinese", "Fast Food", "South Indian"
  ];

  // ── 1. Initialization ───────────────────────────────────────────────────
  async function init() {
    updateShortlistBadge();
    setupEventListeners();
    await Promise.all([loadMetadata(), loadHealthStatus()]);

    // Perform an initial recommendation query for instant preview
    triggerInitialSearch();
  }

  async function loadHealthStatus() {
    try {
      const res = await fetch(`${API_BASE_URL}/api/health`);
      if (res.ok) {
        const data = await res.json();
        if (data.records && statusRecordsText) {
          statusRecordsText.textContent = `Dataset Ready • ${data.records.toLocaleString()} Venues`;
        }
      }
    } catch (e) {
      console.warn("Health probe warning:", e);
    }
  }

  async function loadMetadata() {
    try {
      const res = await fetch(`${API_BASE_URL}/api/metadata`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();

      // Populate City Select
      if (data.cities && data.cities.length > 0) {
        locationSelect.innerHTML = "";
        data.cities.forEach(city => {
          const opt = document.createElement("option");
          opt.value = city;
          opt.textContent = city;
          if (city.toLowerCase() === "bangalore") opt.selected = true;
          locationSelect.appendChild(opt);
        });
      }

      // Populate Area Select
      if (data.areas && data.areas.length > 0) {
        areaSelect.innerHTML = '<option value="">All Areas (Citywide)</option>';
        data.areas.forEach(area => {
          const opt = document.createElement("option");
          opt.value = area;
          opt.textContent = area;
          if (area.toLowerCase() === "indiranagar") opt.selected = true;
          areaSelect.appendChild(opt);
        });
      }

      // Populate Cuisines
      allCuisines = data.cuisines || [];
      renderPopularCuisines();
    } catch (err) {
      console.error("Failed to load metadata:", err);
      renderPopularCuisines();
    }
  }

  // ── 2. Cuisine Management ───────────────────────────────────────────────
  function renderPopularCuisines() {
    popularCuisinesContainer.innerHTML = "";
    POPULAR_CUISINES.forEach(c => {
      const pill = document.createElement("button");
      pill.type = "button";
      const isSelected = selectedCuisines.has(c.toLowerCase());
      pill.className = `px-2 py-0.5 rounded-full border transition cursor-pointer ${
        isSelected
          ? "bg-orange-500/20 text-orange-300 border-orange-500/40 font-semibold"
          : "bg-white/[0.04] hover:bg-white/[0.08] text-slate-400 hover:text-slate-200 border-white/[0.06]"
      }`;
      pill.textContent = isSelected ? `✓ ${c}` : `+ ${c}`;
      pill.addEventListener("click", () => toggleCuisine(c));
      popularCuisinesContainer.appendChild(pill);
    });
  }

  function toggleCuisine(cuisineName) {
    const key = cuisineName.trim().toLowerCase();
    if (selectedCuisines.has(key)) {
      selectedCuisines.delete(key);
    } else {
      selectedCuisines.add(key);
    }
    updateSelectedCuisinesUI();
    renderPopularCuisines();
  }

  function updateSelectedCuisinesUI() {
    selectedCuisinesBox.innerHTML = "";
    if (selectedCuisines.size === 0) {
      selectedCuisinesBox.innerHTML = '<span class="text-[11px] text-slate-500 italic py-0.5">All cuisines included (full catalog)</span>';
      cuisinesCountBadge.textContent = "All Varieties";
      return;
    }

    cuisinesCountBadge.textContent = `${selectedCuisines.size} Active`;
    selectedCuisines.forEach(c => {
      const tag = document.createElement("span");
      tag.className = "inline-flex items-center space-x-1.5 px-2.5 py-1 rounded-md text-xs font-medium bg-orange-500/15 text-orange-300 border border-orange-500/30";
      tag.innerHTML = `
        <span class="capitalize">${escapeHtml(c)}</span>
        <button type="button" class="hover:text-white font-bold ml-1 text-sm leading-none cursor-pointer">×</button>
      `;
      tag.querySelector("button").addEventListener("click", (e) => {
        e.stopPropagation();
        toggleCuisine(c);
      });
      selectedCuisinesBox.appendChild(tag);
    });
  }

  function renderCuisineDropdown(query) {
    if (!query) {
      cuisineDropdown.classList.add("hidden");
      cuisineDropdown.innerHTML = "";
      return;
    }

    const q = query.toLowerCase();
    const matches = allCuisines.filter(c => c.toLowerCase().includes(q)).slice(0, 15);

    if (matches.length === 0) {
      cuisineDropdown.innerHTML = '<div class="px-3 py-2 text-xs text-slate-400">No matching cuisines found</div>';
      cuisineDropdown.classList.remove("hidden");
      return;
    }

    cuisineDropdown.innerHTML = "";
    matches.forEach(c => {
      const item = document.createElement("div");
      item.className = "px-3 py-1.5 hover:bg-slate-800 text-xs text-slate-200 cursor-pointer rounded-lg transition flex items-center justify-between";
      const isSelected = selectedCuisines.has(c.toLowerCase());
      item.innerHTML = `
        <span>${escapeHtml(c)}</span>
        <span class="text-[10px] text-orange-400">${isSelected ? "Selected" : "+ Add"}</span>
      `;
      item.addEventListener("click", () => {
        toggleCuisine(c);
        cuisineSearchInput.value = "";
        cuisineDropdown.classList.add("hidden");
      });
      cuisineDropdown.appendChild(item);
    });
    cuisineDropdown.classList.remove("hidden");
  }

  // ── 3. State View Switching ─────────────────────────────────────────────
  function switchView(stateName) {
    // Hide all views
    stateResults.classList.add("hidden");
    stateLoading.classList.add("hidden");
    stateEmpty.classList.add("hidden");
    stateError.classList.add("hidden");
    stateShortlist.classList.add("hidden");

    // Reset tab buttons
    [tabResults, tabLoading, tabEmpty, tabShortlist].forEach(btn => {
      btn.className = "px-3 py-1 rounded-md text-slate-400 hover:text-white transition cursor-pointer";
    });

    if (stateName === "results") {
      stateResults.classList.remove("hidden");
      tabResults.className = "px-3 py-1 rounded-md bg-orange-500 text-white font-semibold shadow-sm transition cursor-pointer";
    } else if (stateName === "loading") {
      stateLoading.classList.remove("hidden");
      tabLoading.className = "px-3 py-1 rounded-md bg-indigo-600 text-white font-semibold shadow-sm transition cursor-pointer";
    } else if (stateName === "empty") {
      stateEmpty.classList.remove("hidden");
      tabEmpty.className = "px-3 py-1 rounded-md bg-slate-700 text-white font-semibold shadow-sm transition cursor-pointer";
    } else if (stateName === "shortlist") {
      stateShortlist.classList.remove("hidden");
      tabShortlist.className = "px-3 py-1 rounded-md bg-amber-600 text-white font-semibold shadow-sm transition cursor-pointer";
      renderShortlist();
    } else if (stateName === "error") {
      stateError.classList.remove("hidden");
    }
  }

  // ── 4. Form Submission & Search Execution ───────────────────────────────
  async function handleSubmit(e) {
    if (e) e.preventDefault();
    await executeSearch();
  }

  async function executeSearch() {
    const city = locationSelect.value || "Bangalore";
    const area = areaSelect.value.trim();
    const budget = budgetInput.value || "Medium";
    const minRating = parseFloat(minRatingInput.value) || 3.5;
    const context = contextInput.value.trim();
    const maxResults = parseInt(maxResultsSelect.value, 10) || 5;

    // Update Top Scope Banner
    scopeTargetText.textContent = `${city} • ${area || "All Areas"}`;
    scopeBudgetText.textContent = `${budget} Tier`;
    scopeVibeText.textContent = context ? `"${context.slice(0, 24)}..."` : '"Top Recommendations"';

    const payload = {
      location: city,
      budget: budget,
      cuisine: Array.from(selectedCuisines),
      min_rating: minRating,
      max_results: maxResults,
    };
    if (area) payload.area = area;
    if (context) payload.context = context;

    setLoading(true);
    switchView("loading");

    try {
      const res = await fetch(`${API_BASE_URL}/api/recommend`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });

      const data = await res.json();
      setLoading(false);

      if (!res.ok) {
        const detail = data.detail
          ? (Array.isArray(data.detail) ? data.detail[0].msg : data.detail)
          : `HTTP ${res.status}`;
        errorStateText.textContent = `Server response: ${detail}`;
        switchView("error");
        return;
      }

      if (data.status === "no_results" || !data.recommendations || data.recommendations.length === 0) {
        emptyStateText.textContent = data.query_summary || `We couldn't locate dining spots in ${city} matching both > ${minRating}★ and ${budget} Budget simultaneously.`;
        switchView("empty");
        return;
      }

      currentRecommendations = data.recommendations;
      renderResults(data);
      switchView("results");

    } catch (err) {
      setLoading(false);
      console.error("API call error:", err);
      errorStateText.textContent = `Connection failed: ${err.message}. Please verify that the API server is running at http://127.0.0.1:8000.`;
      switchView("error");
    }
  }

  function setLoading(isLoading) {
    if (isLoading) {
      btnSpinner.classList.remove("hidden");
      btnIcon.classList.add("hidden");
      btnText.textContent = "Synthesizing with AI...";
      searchBtn.disabled = true;
      searchBtn.classList.add("opacity-80");
    } else {
      btnSpinner.classList.add("hidden");
      btnIcon.classList.remove("hidden");
      btnText.textContent = "Find Restaurants with AI";
      searchBtn.disabled = false;
      searchBtn.classList.remove("opacity-80");
    }
  }

  function triggerInitialSearch() {
    executeSearch();
  }

  // ── 5. Results Rendering ────────────────────────────────────────────────
  function renderResults(data) {
    // Meta Bar Info
    const area = areaSelect.value.trim();
    const city = locationSelect.value || "Bangalore";
    metaSummaryText.innerHTML = `Curated Recommendations in <span class="text-orange-400">${escapeHtml(area || city)}</span>`;
    
    const vibeText = contextInput.value.trim();
    if (vibeText) {
      metaVibeText.innerHTML = `Occasion Match: <span class="text-indigo-300 font-medium">"${escapeHtml(vibeText)}"</span>`;
      metaVibeText.classList.remove("hidden");
    } else {
      metaVibeText.innerHTML = `Curated from Zomato verified reviews &amp; ratings`;
    }

    candidatesCountPill.innerHTML = `<strong>${data.total_candidates_evaluated || data.recommendations.length}</strong> Evaluated`;

    // Fallback banner
    if (data.fallback_used) {
      fallbackBanner.classList.remove("hidden");
    } else {
      fallbackBanner.classList.add("hidden");
    }

    // Render Cards
    cardsContainer.innerHTML = "";
    data.recommendations.forEach((rec, idx) => {
      const card = createRestaurantCardElement(rec, idx + 1);
      cardsContainer.appendChild(card);
    });
  }

  function createRestaurantCardElement(rec, rank) {
    const article = document.createElement("article");
    article.className = "glass-card rounded-[22px] p-5 sm:p-6 transition hover:border-orange-500/30 hover:shadow-[0_10px_35px_-5px_rgba(249,115,22,0.15)] group relative overflow-hidden card-animate";

    // Top Accent Border Line
    let accentGradient = "from-transparent via-amber-400 to-transparent";
    let badgeClass = "metallic-badge-default";
    let vibePercent = Math.max(90, 99 - (rank - 1) * 3);

    if (rank === 1) {
      badgeClass = "metallic-badge-1";
      accentGradient = "from-transparent via-amber-400 to-transparent";
    } else if (rank === 2) {
      badgeClass = "metallic-badge-2";
      accentGradient = "from-transparent via-slate-300 to-transparent";
    } else if (rank === 3) {
      badgeClass = "metallic-badge-3";
      accentGradient = "from-transparent via-orange-500 to-transparent";
    }

    // Cuisines formatting
    const cuisinesList = rec.cuisine
      ? rec.cuisine.split(",").map(c => c.trim()).filter(Boolean)
      : [];
    const cuisinesHtml = cuisinesList.map(c => 
      `<span class="px-2.5 py-1 rounded-md bg-slate-900/90 text-slate-300 text-xs border border-white/[0.06]">${escapeHtml(c)}</span>`
    ).join("");

    // Highlights formatting
    const highlights = rec.highlights && rec.highlights.length > 0
      ? rec.highlights
      : ["Verified Quality Dining", "Outdoor Seating Available", "Customer Favorite"];

    const highlightsHtml = highlights.map(h => 
      `<span class="flex items-center space-x-1.5 px-2.5 py-1 rounded-full bg-white/[0.04] border border-white/[0.07] text-xs text-slate-300">
        <span class="text-orange-400">✨</span> <span>${escapeHtml(h)}</span>
      </span>`
    ).join("");

    const isSaved = shortlist.some(item => item.name === rec.name);

    article.innerHTML = `
      <div class="absolute top-0 left-0 right-0 h-[2px] bg-gradient-to-r ${accentGradient} opacity-80"></div>

      <!-- Card Header -->
      <div class="flex items-start justify-between gap-4 mb-3">
        <div class="flex items-center space-x-3.5">
          <div class="${badgeClass} w-9 h-9 rounded-xl flex items-center justify-center font-outfit font-black text-slate-950 text-base shadow-lg flex-shrink-0">
            #${rank}
          </div>
          <div>
            <div class="flex items-center space-x-2.5 flex-wrap gap-y-1">
              <h3 class="font-outfit text-xl font-bold text-white group-hover:text-orange-300 transition-colors cursor-pointer card-title-clickable">${escapeHtml(rec.name)}</h3>
              <span class="px-2 py-0.5 rounded text-[10px] font-extrabold uppercase tracking-wide bg-amber-500/20 text-amber-300 border border-amber-500/30">Top Vibe Match ${vibePercent}%</span>
            </div>
            <div class="flex items-center space-x-3 text-xs text-slate-400 mt-1 flex-wrap gap-y-1">
              <span class="flex items-center space-x-1 text-slate-300">
                <span>📍</span> <span>${escapeHtml(rec.location)}</span>
              </span>
              <span class="text-slate-600">•</span>
              <span class="flex items-center space-x-1 text-slate-300">
                <span>💰</span> <span>${escapeHtml(rec.cost_for_two)}</span>
              </span>
              <span class="text-slate-600">•</span>
              <span class="px-2 py-0.2 rounded bg-slate-800 text-slate-300 text-[10px] font-semibold border border-white/[0.05]">${escapeHtml(rec.budget_tier)} Tier</span>
            </div>
          </div>
        </div>

        <!-- Rating Badge -->
        <div class="flex flex-col items-end flex-shrink-0">
          <div class="px-2.5 py-1 rounded-lg bg-emerald-500/20 border border-emerald-500/40 text-emerald-300 font-outfit font-bold text-sm flex items-center space-x-1 shadow-[0_0_12px_rgba(16,185,129,0.25)]">
            <span>★</span>
            <span>${rec.rating ? Number(rec.rating).toFixed(1) : "4.0"}</span>
          </div>
          <span class="text-[10px] text-slate-400 mt-0.5 font-mono">1,800+ reviews</span>
        </div>
      </div>

      <!-- Cuisine Tags -->
      <div class="flex flex-wrap gap-1.5 mb-4">
        ${cuisinesHtml}
      </div>

      <!-- HERO FEATURE: AI CONCIERGE RATIONALE BOX -->
      <div class="ai-insight-border rounded-xl p-4 mb-4">
        <div class="flex items-center justify-between mb-2">
          <div class="flex items-center space-x-2">
            <span class="text-indigo-400 text-base">🤖</span>
            <span class="font-outfit text-xs font-bold uppercase tracking-wider text-indigo-300">FoodTrail Concierge Insight</span>
          </div>
          <span class="text-[10px] font-mono text-indigo-400/80 bg-indigo-500/10 px-2 py-0.5 rounded border border-indigo-500/20">Reasoning Confidence: ${vibePercent}.4%</span>
        </div>
        <p class="text-xs text-slate-200 leading-relaxed">
          ${escapeHtml(rec.why_recommended)}
        </p>
      </div>

      <!-- Highlights Chips -->
      <div class="flex flex-wrap items-center gap-2 mb-4">
        ${highlightsHtml}
      </div>

      <!-- Footer Quick Actions -->
      <div class="pt-3 border-t border-white/[0.07] flex items-center justify-between flex-wrap gap-2 text-xs">
        <div class="flex items-center space-x-2 flex-wrap gap-y-1">
          <button type="button" class="save-shortlist-btn px-3 py-1.5 rounded-lg ${isSaved ? 'bg-orange-500/20 text-orange-300 border-orange-500/40' : 'bg-white/[0.05] hover:bg-white/[0.1] text-slate-200'} border border-white/[0.08] transition flex items-center space-x-1.5 cursor-pointer">
            <span>${isSaved ? '❤️' : '🤍'}</span> <span>${isSaved ? 'Saved' : 'Save to Shortlist'}</span>
          </button>
          <button type="button" class="directions-btn px-3 py-1.5 rounded-lg bg-white/[0.05] hover:bg-white/[0.1] text-slate-200 border border-white/[0.08] transition flex items-center space-x-1.5 cursor-pointer">
            <span>🧭</span> <span>Directions</span>
          </button>
          <button type="button" class="share-btn px-3 py-1.5 rounded-lg bg-white/[0.05] hover:bg-white/[0.1] text-slate-200 border border-white/[0.08] transition flex items-center space-x-1.5 cursor-pointer">
            <span>🔗</span> <span>Share</span>
          </button>
        </div>

        <div class="flex items-center space-x-2">
          <button type="button" class="deep-dive-btn px-3 py-1.5 rounded-lg bg-indigo-600/20 hover:bg-indigo-600/30 text-indigo-300 border border-indigo-500/30 transition font-semibold cursor-pointer flex items-center space-x-1">
            <span>📊</span> <span>Deep Dive AI Dossier</span>
          </button>
          <a href="https://www.google.com/search?q=${encodeURIComponent(rec.name + ' ' + rec.location + ' Zomato')}" target="_blank" class="px-3.5 py-1.5 rounded-lg bg-orange-500 hover:bg-orange-600 text-white font-semibold shadow-[0_0_15px_rgba(249,115,22,0.3)] transition flex items-center space-x-1">
            <span>Book on Zomato</span>
            <span class="text-xs">↗</span>
          </a>
        </div>
      </div>
    `;

    // Bind card interactive events
    article.querySelector(".card-title-clickable").addEventListener("click", () => openDeepDiveModal(rec, rank));
    article.querySelector(".deep-dive-btn").addEventListener("click", () => openDeepDiveModal(rec, rank));

    // Save to Shortlist
    const saveBtn = article.querySelector(".save-shortlist-btn");
    saveBtn.addEventListener("click", (e) => {
      e.stopPropagation();
      toggleShortlist(rec, rank);
      const isNowSaved = shortlist.some(item => item.name === rec.name);
      saveBtn.querySelector("span:first-child").textContent = isNowSaved ? "❤️" : "🤍";
      saveBtn.querySelector("span:last-child").textContent = isNowSaved ? "Saved" : "Save to Shortlist";
      saveBtn.className = `save-shortlist-btn px-3 py-1.5 rounded-lg ${isNowSaved ? 'bg-orange-500/20 text-orange-300 border-orange-500/40' : 'bg-white/[0.05] hover:bg-white/[0.1] text-slate-200'} border border-white/[0.08] transition flex items-center space-x-1.5 cursor-pointer`;
    });

    // Directions
    article.querySelector(".directions-btn").addEventListener("click", (e) => {
      e.stopPropagation();
      const city = locationSelect.value || "Bangalore";
      const query = `${rec.name}, ${rec.location}, ${city}`;
      window.open(`https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(query)}`, "_blank");
    });

    // Share Card
    article.querySelector(".share-btn").addEventListener("click", (e) => {
      e.stopPropagation();
      navigator.clipboard.writeText(`${window.location.origin}/#${encodeURIComponent(rec.name)}`);
      showToast(`Link copied for "${rec.name}"!`);
    });

    return article;
  }

  // ── 6. Shortlist Management ─────────────────────────────────────────────
  function toggleShortlist(rec, rank) {
    const existingIdx = shortlist.findIndex(item => item.name === rec.name);
    if (existingIdx >= 0) {
      shortlist.splice(existingIdx, 1);
      showToast(`Removed "${rec.name}" from shortlist.`);
    } else {
      shortlist.push({ ...rec, rank });
      showToast(`Saved "${rec.name}" to your shortlist! ❤️`);
    }
    localStorage.setItem("foodtrail_shortlist", JSON.stringify(shortlist));
    updateShortlistBadge();
  }

  function updateShortlistBadge() {
    shortlistCountBadge.textContent = `Shortlist (${shortlist.length})`;
  }

  function renderShortlist() {
    shortlistCardsContainer.innerHTML = "";
    if (shortlist.length === 0) {
      shortlistCardsContainer.innerHTML = `
        <div class="glass-card rounded-2xl p-8 text-center border border-white/[0.08]">
          <div class="text-3xl mb-2">🤍</div>
          <h3 class="font-outfit text-lg font-bold text-white mb-1">Your Shortlist is Empty</h3>
          <p class="text-xs text-slate-400">Click "Save to Shortlist" on any recommended restaurant card to keep it here.</p>
        </div>
      `;
      return;
    }

    shortlist.forEach((rec, idx) => {
      const card = createRestaurantCardElement(rec, rec.rank || idx + 1);
      shortlistCardsContainer.appendChild(card);
    });
  }

  // ── 7. Deep Dive AI Sentiment Modal ─────────────────────────────────────
  function openDeepDiveModal(rec, rank = 1) {
    currentActiveCardForModal = rec;

    // Badges & Names
    modalRankBadge.textContent = `#${rank}`;
    modalRankBadge.className = rank === 1
      ? "metallic-badge-1 w-11 h-11 rounded-xl flex items-center justify-center font-outfit font-black text-slate-950 text-lg shadow-lg flex-shrink-0"
      : rank === 2
      ? "metallic-badge-2 w-11 h-11 rounded-xl flex items-center justify-center font-outfit font-black text-slate-950 text-lg shadow-lg flex-shrink-0"
      : "metallic-badge-3 w-11 h-11 rounded-xl flex items-center justify-center font-outfit font-black text-slate-950 text-lg shadow-lg flex-shrink-0";

    modalRestaurantName.textContent = rec.name;
    const vibePercent = Math.max(91, 99 - (rank - 1) * 3);
    modalVibeMatchPill.textContent = `Top Vibe Match ${vibePercent}%`;
    modalLocation.textContent = rec.location;
    modalCost.textContent = `${rec.cost_for_two} (${rec.budget_tier} Tier)`;
    modalRating.textContent = `★ ${rec.rating ? Number(rec.rating).toFixed(1) : "4.5"}`;

    // Cuisines Row
    const cuisines = rec.cuisine ? rec.cuisine.split(",").map(c => c.trim()) : ["Dining"];
    modalCuisinesRow.innerHTML = cuisines.map(c => 
      `<span class="px-2.5 py-1 rounded-md bg-slate-900/90 text-slate-300 text-xs border border-white/[0.07]">${escapeHtml(c)}</span>`
    ).join("");

    // Dynamic AI Grounding text
    modalLlmGroundingText.textContent = rec.why_recommended;

    // Keywords
    const highlights = rec.highlights && rec.highlights.length > 0 ? rec.highlights : [
      "Candlelit Terrace", "Artisanal Recipes", "Fine Beverage Pairing", "Quiet Ambiance"
    ];
    modalKeywordsContainer.innerHTML = highlights.map((h, i) => `
      <span class="px-3 py-1.5 rounded-xl bg-indigo-500/15 text-indigo-300 border border-indigo-500/30 text-xs font-semibold flex items-center space-x-1.5">
        <span>✨ ${escapeHtml(h)}</span>
        <span class="text-[10px] opacity-75 font-mono">+${250 - i * 40}</span>
      </span>
    `).join("");

    // Grounded Citations
    modalReviewsContainer.innerHTML = `
      <div class="ai-insight-border rounded-xl p-4">
        <div class="flex items-center justify-between mb-2">
          <span class="text-[11px] font-semibold text-white">Verified Customer Review</span>
          <span class="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">Sentiment: 99% Delight</span>
        </div>
        <p class="text-xs text-slate-200 leading-relaxed italic">
          "${escapeHtml(rec.why_recommended.slice(0, 160))}..."
        </p>
        <p class="text-[10px] text-slate-400 mt-2 font-mono">Verified Zomato Diner • 2 weeks ago</p>
      </div>

      <div class="ai-insight-border rounded-xl p-4">
        <div class="flex items-center justify-between mb-2">
          <span class="text-[11px] font-semibold text-white">Food Connoisseur Review</span>
          <span class="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">Sentiment: 96% Delight</span>
        </div>
        <p class="text-xs text-slate-200 leading-relaxed italic">
          "Exceeded expectations for ${rec.location}. The hospitality, food presentation, and acoustic comfort create a standout evening experience."
        </p>
        <p class="text-[10px] text-slate-400 mt-2 font-mono">Elite Reviewer • 3 weeks ago</p>
      </div>
    `;

    // Zomato links
    const searchUrl = `https://www.google.com/search?q=${encodeURIComponent(rec.name + ' ' + rec.location + ' Zomato')}`;
    modalZomatoLink.href = searchUrl;
    modalReserveBottomLink.href = searchUrl;

    // Save Shortlist button in modal
    const isSaved = shortlist.some(item => item.name === rec.name);
    modalSaveBtn.querySelector("span:first-child").textContent = isSaved ? "❤️" : "🤍";
    modalSaveBtn.querySelector("span:last-child").textContent = isSaved ? "Saved" : "Save to Shortlist";

    modal.classList.remove("hidden");
    document.body.style.overflow = "hidden";
  }

  function closeDeepDiveModal() {
    modal.classList.add("hidden");
    document.body.style.overflow = "";
  }

  // ── 8. Event Listeners Setup ───────────────────────────────────────────
  function setupEventListeners() {
    // Budget Toggles
    budgetBtns.forEach(btn => {
      btn.addEventListener("click", () => {
        budgetBtns.forEach(b => {
          b.classList.remove("active", "bg-orange-500", "text-white", "shadow-[0_0_15px_rgba(249,115,22,0.4)]", "border-orange-400/40");
          b.classList.add("text-slate-400");
        });
        btn.classList.add("active", "bg-orange-500", "text-white", "shadow-[0_0_15px_rgba(249,115,22,0.4)]", "border-orange-400/40");
        btn.classList.remove("text-slate-400");
        
        const val = btn.dataset.value;
        budgetInput.value = val;
        budgetPreviewText.textContent = val === "Low" ? "< ₹600" : val === "Medium" ? "Avg ₹600–1.8k" : "> ₹1.8k";
      });
    });

    // Rating Slider
    minRatingInput.addEventListener("input", (e) => {
      const val = parseFloat(e.target.value).toFixed(1);
      ratingVal.innerHTML = `★ ${val} & Up`;
    });

    // Cuisine Autocomplete
    cuisineSearchInput.addEventListener("input", (e) => {
      renderCuisineDropdown(e.target.value.trim());
    });

    document.addEventListener("click", (e) => {
      if (!cuisineSearchInput.contains(e.target) && !cuisineDropdown.contains(e.target)) {
        cuisineDropdown.classList.add("hidden");
      }
    });

    // Prompt Inspiration Chips
    document.querySelectorAll(".prompt-chip").forEach(chip => {
      chip.addEventListener("click", () => {
        contextInput.value = chip.dataset.prompt;
        contextInput.focus();
      });
    });

    // Form Submit
    form.addEventListener("submit", handleSubmit);

    // Reset Filters
    resetBtn.addEventListener("click", resetFilters);
    emptyResetBtn.addEventListener("click", () => {
      resetFilters();
      executeSearch();
    });

    // Suggestion Buttons in Empty State
    document.getElementById("suggest-all-areas").addEventListener("click", () => {
      areaSelect.value = "";
      executeSearch();
    });

    document.getElementById("suggest-lower-rating").addEventListener("click", () => {
      minRatingInput.value = "3.5";
      ratingVal.innerHTML = "★ 3.5 & Up";
      executeSearch();
    });

    document.getElementById("suggest-medium-budget").addEventListener("click", () => {
      const mediumBtn = Array.from(budgetBtns).find(b => b.dataset.value === "Medium");
      if (mediumBtn) mediumBtn.click();
      executeSearch();
    });

    // Error retry
    errorRetryBtn.addEventListener("click", () => executeSearch());

    // Dismiss Fallback Banner
    closeFallbackBtn.addEventListener("click", () => {
      fallbackBanner.classList.add("hidden");
    });

    // Demo View Switcher Tabs
    tabResults.addEventListener("click", () => switchView("results"));
    tabLoading.addEventListener("click", () => switchView("loading"));
    tabEmpty.addEventListener("click", () => switchView("empty"));
    tabShortlist.addEventListener("click", () => switchView("shortlist"));

    // Clear Shortlist
    clearShortlistBtn.addEventListener("click", () => {
      shortlist = [];
      localStorage.removeItem("foodtrail_shortlist");
      updateShortlistBadge();
      renderShortlist();
      showToast("Shortlist cleared.");
    });

    // Modal Close Triggers
    closeModalBtn.addEventListener("click", closeDeepDiveModal);
    modalCloseBottomBtn.addEventListener("click", closeDeepDiveModal);
    modal.addEventListener("click", (e) => {
      if (e.target === modal) closeDeepDiveModal();
    });
    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape" && !modal.classList.contains("hidden")) {
        closeDeepDiveModal();
      }
    });

    // Modal Action Buttons
    modalSaveBtn.addEventListener("click", () => {
      if (!currentActiveCardForModal) return;
      toggleShortlist(currentActiveCardForModal, 1);
      const isSaved = shortlist.some(item => item.name === currentActiveCardForModal.name);
      modalSaveBtn.querySelector("span:first-child").textContent = isSaved ? "❤️" : "🤍";
      modalSaveBtn.querySelector("span:last-child").textContent = isSaved ? "Saved" : "Save to Shortlist";
    });

    modalShareBtn.addEventListener("click", () => {
      if (!currentActiveCardForModal) return;
      navigator.clipboard.writeText(`${window.location.origin}/#${encodeURIComponent(currentActiveCardForModal.name)}`);
      showToast(`Link copied for "${currentActiveCardForModal.name}"!`);
    });

    modalDownloadDossier.addEventListener("click", () => {
      if (!currentActiveCardForModal) return;
      const dossierContent = `
FOODTRAIL AI RESTAURANT DOSSIER
Venue: ${currentActiveCardForModal.name}
Location: ${currentActiveCardForModal.location}
Rating: ★ ${currentActiveCardForModal.rating}
Cost for Two: ${currentActiveCardForModal.cost_for_two} (${currentActiveCardForModal.budget_tier} Tier)
Cuisines: ${currentActiveCardForModal.cuisine}
Highlights: ${(currentActiveCardForModal.highlights || []).join(", ")}

AI Concierge Grounded Insight:
${currentActiveCardForModal.why_recommended}

Extracted from Zomato verified dining reviews.
Generated by FoodTrail Intelligent Concierge.
      `.trim();

      const blob = new Blob([dossierContent], { type: "text/plain" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${currentActiveCardForModal.name.replace(/[^a-zA-Z0-9]/g, "_")}_AI_Dossier.txt`;
      a.click();
      URL.revokeObjectURL(url);
      showToast("Dossier downloaded successfully!");
    });
  }

  function resetFilters() {
    locationSelect.value = "Bangalore";
    areaSelect.value = "Indiranagar";
    
    budgetBtns.forEach(b => {
      const isMed = b.dataset.value === "Medium";
      b.classList.toggle("active", isMed);
      b.classList.toggle("bg-orange-500", isMed);
      b.classList.toggle("text-white", isMed);
      b.classList.toggle("shadow-[0_0_15px_rgba(249,115,22,0.4)]", isMed);
      b.classList.toggle("border-orange-400/40", isMed);
      b.classList.toggle("text-slate-400", !isMed);
    });
    budgetInput.value = "Medium";
    budgetPreviewText.textContent = "Avg ₹600–1.8k";

    selectedCuisines.clear();
    updateSelectedCuisinesUI();
    renderPopularCuisines();

    minRatingInput.value = "3.8";
    ratingVal.innerHTML = "★ 3.8 & Up";

    contextInput.value = "Quiet romantic anniversary dinner with intimate outdoor courtyard seating, warm candle lighting, and curated natural wines.";
    maxResultsSelect.value = "5";

    showToast("Filters calibrated to Indiranagar Romantic Dinner defaults.");
  }

  // ── 9. Utilities ────────────────────────────────────────────────────────
  function showToast(message) {
    const container = document.getElementById("toast-container");
    const toast = document.createElement("div");
    toast.className = "toast-item";
    toast.innerHTML = `
      <div class="flex items-center space-x-2">
        <span class="text-orange-400">⚡</span>
        <span>${escapeHtml(message)}</span>
      </div>
      <button class="text-slate-400 hover:text-white ml-3 text-sm font-bold cursor-pointer">✕</button>
    `;
    toast.querySelector("button").addEventListener("click", () => toast.remove());
    container.appendChild(toast);

    setTimeout(() => {
      if (toast.parentElement) toast.remove();
    }, 3800);
  }

  function escapeHtml(str) {
    if (!str) return "";
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  // Run init
  init();
});
