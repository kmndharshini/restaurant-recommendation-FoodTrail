"""Data cleaning, normalization, and budget categorization module."""
import os
import re
import pandas as pd
import numpy as np
from src.config import settings

def preprocess(df: pd.DataFrame) -> pd.DataFrame:
    """Clean and transform the raw Zomato dataset according to project specs."""
    df = df.copy()

    # Standardize column names if needed
    col_mapping = {
        "approx_cost(for two people)": "cost_raw",
        "average_cost_for_two": "cost_raw",
        "rate": "rating_raw",
        "aggregate_rating": "rating_raw",
        "listed_in(city)": "neighborhood"
    }
    df = df.rename(columns={k: v for k, v in col_mapping.items() if k in df.columns})

    # Ensure votes is numeric for sorting duplicates
    if "votes" in df.columns:
        df["votes"] = pd.to_numeric(df["votes"], errors="coerce").fillna(0).astype(int)
    else:
        df["votes"] = 0

    # Identify city column early if present
    city_candidate = next((c for c in ["city", "City", "CITY", "city_name", "City Name"] if c in df.columns), None)

    # Step 1: Drop duplicates on restaurant name + location + city composite key (keep highest votes)
    subset_cols = [c for c in ["name", "location", city_candidate] if c and c in df.columns]
    if subset_cols:
        df = df.sort_values("votes", ascending=False).drop_duplicates(subset=subset_cols)

    # Step 2: Normalize text fields
    if "name" in df.columns:
        df["name"] = df["name"].astype(str).str.strip()

    if "location" in df.columns:
        df["location"] = df["location"].astype(str).str.strip().str.lower()
    elif "locality" in df.columns:
        df["location"] = df["locality"].astype(str).str.strip().str.lower()
    elif "neighborhood" in df.columns:
        df["location"] = df["neighborhood"].astype(str).str.strip().str.lower()
    else:
        df["location"] = "unknown"

    # Use dataset city column if available; fallback to "bangalore" for single-city datasets
    if city_candidate and df[city_candidate].dropna().count() > 0:
        df["city"] = df[city_candidate].astype(str).str.strip().str.lower()
        df["city"] = df["city"].replace({"nan": "unknown", "none": "unknown", "": "unknown"})
    else:
        df["city"] = "bangalore"

    # Step 3: Parse ratings (strip /5, coerce to float, drop NaNs)
    rating_col = "rating_raw" if "rating_raw" in df.columns else ("aggregate_rating" if "aggregate_rating" in df.columns else "rating")
    if rating_col in df.columns:
        extracted_rating = df[rating_col].astype(str).str.extract(r"(\d+(?:\.\d+)?)")[0]
        df["rating"] = pd.to_numeric(extracted_rating, errors="coerce")
    else:
        df["rating"] = np.nan

    # Step 4: Parse cost (remove currency symbols, commas, convert to float)
    cost_col = "cost_raw" if "cost_raw" in df.columns else ("average_cost_for_two" if "average_cost_for_two" in df.columns else "cost")
    if cost_col in df.columns:
        cleaned_cost = df[cost_col].astype(str).str.replace(r"[^\d]", "", regex=True)
        df["cost"] = pd.to_numeric(cleaned_cost, errors="coerce")
    else:
        df["cost"] = np.nan

    # Impute missing cost with median cost before tier assignment if any
    median_cost = df["cost"].median()
    if pd.isna(median_cost) or median_cost <= 0:
        median_cost = 600.0
    df["cost"] = df["cost"].fillna(median_cost)

    # Step 5: Assign budget tiers: Low < ₹600, Medium ₹600–₹1800, High > ₹1800
    df["budget_tier"] = pd.cut(
        df["cost"],
        bins=[0, 600, 1800, float("inf")],
        labels=["Low", "Medium", "High"],
        right=False
    ).astype(str)

    # Step 6: Parse cuisines into list column for overlap matching
    cuisine_col = "cuisines" if "cuisines" in df.columns else ("cuisine" if "cuisine" in df.columns else None)
    if cuisine_col and cuisine_col in df.columns:
        def _parse_cuisines(val):
            if not isinstance(val, str) or pd.isna(val):
                return []
            return [c.strip().lower() for c in val.split(",") if c.strip() and c.strip().lower() != "nan"]

        df["cuisines_list"] = df[cuisine_col].apply(_parse_cuisines)
    else:
        df["cuisines_list"] = [[] for _ in range(len(df))]

    # Step 7: Compute popularity score: score = rating * log1p(votes)
    df["popularity_score"] = df["rating"].fillna(0) * np.log1p(df["votes"])

    # Step 8: Drop invalid rows missing critical identifiers or ratings
    df = df.dropna(subset=["name", "city", "rating", "cost", "budget_tier"])

    # Reset index and return
    return df.reset_index(drop=True)

def save_processed(df: pd.DataFrame, path: str = settings.PROCESSED_DATA_PATH):
    """Save cleaned DataFrame to parquet format."""
    parent_dir = os.path.dirname(path)
    if parent_dir:
        os.makedirs(parent_dir, exist_ok=True)
    df.to_parquet(path, index=False)

if __name__ == "__main__":
    from src.data.ingest import ingest_dataset
    print("Starting data ingestion and preprocessing pipeline...")
    raw_df = ingest_dataset()
    print(f"Raw data loaded: {len(raw_df)} rows.")
    processed_df = preprocess(raw_df)
    save_processed(processed_df)
    print(f"Preprocessed dataset saved to {settings.PROCESSED_DATA_PATH} with {len(processed_df)} rows.")
