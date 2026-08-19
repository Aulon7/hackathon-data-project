"""Kosovo-only World Bank series (country code XKX). No key needed."""
import pandas as pd
import requests

from .common import retry_get

WB_URL = "https://api.worldbank.org/v2/country/XKX/indicator/{code}"

def fetch_inflation() -> pd.DataFrame:
    """Kosovo CPI inflation, annual %. Columns: year, inflation_pct."""
    r = retry_get(WB_URL.format(code="FP.CPI.TOTL.ZG"),
                     params={"format": "json", "per_page": 100})
    r.raise_for_status()
    rows = r.json()[1]
    df = pd.DataFrame([{"year": int(x["date"]), "inflation_pct": x["value"]}
                       for x in rows if x["value"] is not None])
    return df.sort_values("year").reset_index(drop=True)
