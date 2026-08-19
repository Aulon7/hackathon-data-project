"""Live-first fetching with explicit provenance and safe Parquet fallbacks."""
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd

FALLBACK_DIR = Path(__file__).resolve().parent.parent / "data" / "fallback"


@dataclass
class DatasetResult:
    data: pd.DataFrame
    status: str  # "live" or "fallback"
    source: str
    retrieved_at: str
    fallback_path: str | None = None

    @property
    def coverage(self) -> str:
        for column in ("date", "year"):
            if column in self.data:
                values = self.data[column]
                return f"{values.min()} to {values.max()}"
        return "not available"


def load_with_fallback(name: str, fetch_fn, source: str, *, refresh_snapshot: bool = False) -> DatasetResult:
    """Fetch live data, otherwise use the shipped snapshot.

    Snapshots are deliberately immutable during ordinary app use. Set
    ``refresh_snapshot=True`` only in an explicit maintenance command.
    """
    path = FALLBACK_DIR / f"{name}.parquet"
    retrieved_at = datetime.now(timezone.utc).isoformat()
    try:
        df = fetch_fn()
        if df is None or df.empty:
            raise ValueError("source returned no rows")
        if refresh_snapshot:
            FALLBACK_DIR.mkdir(parents=True, exist_ok=True)
            df.to_parquet(path, index=False)
        return DatasetResult(df, "live", source, retrieved_at, str(path) if path.exists() else None)
    except Exception as exc:
        if path.exists():
            print(f"[fallback] live fetch of '{name}' failed ({exc}); using snapshot")
            return DatasetResult(pd.read_parquet(path), "fallback", source, retrieved_at, str(path))
        raise RuntimeError(f"{name}: live fetch failed and no fallback snapshot exists") from exc

def with_fallback(name: str, fetch_fn, source: str = "unspecified") -> pd.DataFrame:
    """Compatibility wrapper returning only a DataFrame.

    New application code should use :func:`load_with_fallback` to expose status.
    """
    return load_with_fallback(name, fetch_fn, source).data

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
