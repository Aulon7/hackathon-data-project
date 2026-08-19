"""Live-first fetching with a parquet fallback so the demo survives API outages."""
from pathlib import Path
import pandas as pd

FALLBACK_DIR = Path(__file__).resolve().parent.parent / "data" / "fallback"

def with_fallback(name: str, fetch_fn):
    """Call fetch_fn(); on success snapshot to parquet, on failure load the last snapshot."""
    path = FALLBACK_DIR / f"{name}.parquet"
    try:
        df = fetch_fn()
        if df is not None and len(df):
            FALLBACK_DIR.mkdir(parents=True, exist_ok=True)
            df.to_parquet(path, index=False)
        return df
    except Exception as exc:
        if path.exists():
            print(f"[fallback] live fetch of '{name}' failed ({exc}); using snapshot")
            return pd.read_parquet(path)
        raise

def retry_get(url, params=None, tries: int = 3, timeout: int = 30):
    """GET with simple retries — public statistics APIs flake on conference wifi."""
    import time
    import requests
    last = None
    for i in range(tries):
        try:
            r = requests.get(url, params=params, timeout=timeout,
                             headers={"User-Agent": "kosovo-farmer-app/1.0"})
            r.raise_for_status()
            return r
        except Exception as exc:
            last = exc
            time.sleep(1 + i)
    raise last
