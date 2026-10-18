"""Dataset ingestion module from Hugging Face."""
import os
import tempfile
import pandas as pd
from datasets import load_dataset
from huggingface_hub import hf_hub_download
from src.config import settings

def _configure_cache():
    """Ensure Hugging Face and temporary cache directories use workspace drive to prevent disk space exhaustion."""
    cache_dir = os.path.abspath(".hf_cache")
    os.makedirs(cache_dir, exist_ok=True)
    os.environ["HF_HOME"] = cache_dir
    os.environ["HF_HUB_CACHE"] = cache_dir
    os.environ["TEMP"] = cache_dir
    os.environ["TMP"] = cache_dir
    tempfile.tempdir = cache_dir

def ingest_dataset(dataset_id: str = settings.DATASET_ID) -> pd.DataFrame:
    """Download Zomato dataset from Hugging Face and return as DataFrame."""
    raw_parquet_path = "data/raw/zomato_raw.parquet"
    raw_csv_path = "data/raw/zomato.csv"

    # Fast path: already saved as parquet
    if os.path.exists(raw_parquet_path):
        return pd.read_parquet(raw_parquet_path)

    # If raw CSV exists, convert and cache
    if os.path.exists(raw_csv_path):
        try:
            df = pd.read_csv(raw_csv_path, low_memory=False)
        except (UnicodeDecodeError, Exception):
            df = pd.read_csv(raw_csv_path, encoding="latin-1", low_memory=False)
        os.makedirs("data/raw", exist_ok=True)
        df.to_parquet(raw_parquet_path, index=False)
        return df

    _configure_cache()
    try:
        # Direct hub download of zomato.csv into data/raw
        os.makedirs("data/raw", exist_ok=True)
        downloaded = hf_hub_download(
            repo_id=dataset_id,
            filename="zomato.csv",
            repo_type="dataset",
            local_dir="data/raw"
        )
        df = pd.read_csv(downloaded)
    except Exception:
        # Fallback to load_dataset
        dataset = load_dataset(dataset_id, split="train")
        df = dataset.to_pandas()

    os.makedirs("data/raw", exist_ok=True)
    df.to_parquet(raw_parquet_path, index=False)
    return df

if __name__ == "__main__":
    print(f"Ingesting dataset: {settings.DATASET_ID}")
    df = ingest_dataset()
    print(f"Ingested {len(df)} records successfully into data/raw/zomato_raw.parquet.")
