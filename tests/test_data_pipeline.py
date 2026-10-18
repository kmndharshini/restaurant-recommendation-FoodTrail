"""Unit and validation tests for Phase 2: Data Ingestion and Preprocessing Pipeline."""
import os
import pandas as pd
import numpy as np
import pytest
from src.data.ingest import ingest_dataset
from src.data.preprocess import preprocess, save_processed
from src.config import settings

def test_raw_dataset_exists_and_loadable():
    """Verify data/raw/zomato_raw.parquet exists and contains expected records."""
    assert os.path.exists("data/raw/zomato_raw.parquet"), "Raw parquet file should exist"
    raw_df = pd.read_parquet("data/raw/zomato_raw.parquet")
    assert len(raw_df) > 1000, f"Expected >1000 raw rows, got {len(raw_df)}"
    assert "name" in raw_df.columns

def test_processed_dataset_exists_and_loadable():
    """Verify data/processed/restaurants.parquet exists and is populated."""
    assert os.path.exists(settings.PROCESSED_DATA_PATH), f"Processed file {settings.PROCESSED_DATA_PATH} should exist"
    df = pd.read_parquet(settings.PROCESSED_DATA_PATH)
    assert len(df) > 1000, f"Expected >1000 processed rows, got {len(df)}"

def test_no_nulls_in_critical_columns():
    """Verify no nulls exist in required columns."""
    df = pd.read_parquet(settings.PROCESSED_DATA_PATH)
    critical_cols = ["name", "city", "rating", "cost", "budget_tier"]
    for col in critical_cols:
        assert col in df.columns, f"Missing critical column: {col}"
        null_count = df[col].isnull().sum()
        assert null_count == 0, f"Column {col} has {null_count} null values"

def test_budget_tier_values_valid():
    """Verify budget_tier values are strictly 'Low', 'Medium', or 'High'."""
    df = pd.read_parquet(settings.PROCESSED_DATA_PATH)
    allowed_tiers = {"Low", "Medium", "High"}
    actual_tiers = set(df["budget_tier"].unique())
    assert actual_tiers.issubset(allowed_tiers), f"Unexpected budget tiers: {actual_tiers - allowed_tiers}"

def test_cuisines_list_is_valid_list():
    """Verify cuisines_list contains non-empty lists of lowercase strings."""
    df = pd.read_parquet(settings.PROCESSED_DATA_PATH)
    assert "cuisines_list" in df.columns
    sample = df["cuisines_list"].iloc[0]
    assert isinstance(sample, (list, np.ndarray)), f"cuisines_list must be list or array, got {type(sample)}"
    
    # Check that entries in lists are lowercase strings
    all_elements = [c for sublist in df["cuisines_list"].head(100) for c in sublist]
    assert all(isinstance(c, str) and c == c.lower() for c in all_elements)

def test_popularity_score_is_non_negative_and_finite():
    """Verify popularity_score is non-negative and finite."""
    df = pd.read_parquet(settings.PROCESSED_DATA_PATH)
    assert "popularity_score" in df.columns
    assert (df["popularity_score"] >= 0).all()
    assert np.isfinite(df["popularity_score"]).all()

def test_preprocess_synthetic_edge_cases():
    """Test preprocessing with dirty edge cases: 'NEW', '-', currency symbols, missing cost."""
    dirty_data = pd.DataFrame({
        "name": ["Cafe One", "Cafe Two", "Cafe Three", "Cafe Four", "Cafe One"],
        "location": ["indiranagar", "koramangala", "whitefield", "indiranagar", "indiranagar"],
        "rate": ["4.2/5", "NEW", "-", "3.8 / 5", "4.2/5"],
        "approx_cost(for two people)": ["₹800", "500", "1,500", None, "₹800"],
        "cuisines": ["Italian, Pizza", "Chinese", "Continental", "Cafe", "Italian, Pizza"],
        "votes": [100, 20, 5, 50, 10]
    })
    cleaned = preprocess(dirty_data)
    
    # Cafe One should be deduplicated (keeping higher vote version: 100 votes)
    assert len(cleaned[cleaned["name"] == "Cafe One"]) == 1
    # Cafe Two ('NEW') and Cafe Three ('-') should be dropped because rating is NaN
    assert "Cafe Two" not in cleaned["name"].values
    assert "Cafe Three" not in cleaned["name"].values
    # Cafe Four with missing cost should have cost imputed from median
    assert "Cafe Four" in cleaned["name"].values
    assert cleaned.loc[cleaned["name"] == "Cafe Four", "cost"].iloc[0] > 0
