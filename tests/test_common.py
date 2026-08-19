import pandas as pd

from ingest.common import FALLBACK_DIR, load_with_fallback


def test_fallback_is_used_and_not_overwritten(tmp_path, monkeypatch):
    monkeypatch.setattr("ingest.common.FALLBACK_DIR", tmp_path)
    snapshot = tmp_path / "demo.parquet"
    pd.DataFrame({"date": pd.to_datetime(["2024-01-01"]), "value": [1]}).to_parquet(snapshot, index=False)

    def unavailable():
        raise ConnectionError("offline")

    result = load_with_fallback("demo", unavailable, "example")
    assert result.status == "fallback"
    assert result.data.iloc[0]["value"] == 1
    assert snapshot.exists()
