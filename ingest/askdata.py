"""ASKdata (Kosovo Agency of Statistics) ingest via the PxWeb JSON API. No key needed.

Three tables power the app:
  - ICPB04.px            monthly farm-gate prices for 32 products (2022-M01 ->)
  - ICPB03.px            monthly agricultural OUTPUT price index (2015-M01 ->)
  - indeksi-mujore.px    monthly agricultural INPUT price index, 2020=100 (2015-M01 ->)

PxWeb quirks handled here (all discovered against the live API):
  - path segments are Albanian and must be encoded exactly as the navigation API
    returns them (note 'te`' vs 'te"' and a double space in one folder name);
  - variable codes are case-sensitive AND differ between tables ('Viti' vs 'viti');
  - omitted dimensions get ELIMINATED to a single default value, and this PxWeb
    version ignores the '*' filter -> we fetch each table's metadata first and
    request every dimension's full code list explicitly;
  - month labels are full names in one table ('January') and abbreviated in
    another ('Jan').
"""
import calendar

import pandas as pd
import requests
from pyjstat import pyjstat

BASE = "https://askdata.rks-gov.net/api/v1/en/ASKdata"

_PRICE_FOLDER = [
    "Agriculture",
    "Agriculture Price and Price Index",
]
_OUTPUT_NODE = _PRICE_FOLDER + [
    "Indeksi i \u00c7mimeve t\u00eb Prodhimit dhe \u00c7mimet n\u00eb Bujq\u00ebsi",
    "Quarterly Output Price Index and Prices in Agriculture",
]
_INPUT_NODE = _PRICE_FOLDER + [
    "Indeksi i \u00c7mimeve t\u00e8 Inputeve dhe \u00c7mimet n\u00eb Bujq\u00ebsi",
    "Quarterly  Input Price Index and Prices in Agriculture",  # double space is real
]

_MONTHS = {name: i for i, name in enumerate(calendar.month_name) if name}
_MONTHS.update({abbr: i for i, abbr in enumerate(calendar.month_abbr) if abbr})


def _url(segments):
    return BASE + "/" + "/".join(requests.utils.quote(s, safe="") for s in segments)


def _fetch_full(segments, filters: dict | None = None) -> pd.DataFrame:
    """Fetch a PxWeb table as a tidy DataFrame, requesting EVERY dimension
    explicitly (metadata-driven) so nothing gets silently eliminated.
    `filters` overrides the value list for specific dimension codes."""
    filters = filters or {}
    url = _url(segments)
    meta = requests.get(url, timeout=60)
    meta.raise_for_status()
    query = [{"code": v["code"],
              "selection": {"filter": "item",
                            "values": filters.get(v["code"], v["values"])}}
             for v in meta.json()["variables"]]
    r = requests.post(url, json={"query": query,
                                 "response": {"format": "json-stat2"}}, timeout=60)
    r.raise_for_status()
    return pyjstat.Dataset.read(r.text).write("dataframe")


def _col(df, needle):
    """Find the column whose name contains `needle` (dimension labels vary per table)."""
    for c in df.columns:
        if needle in c.lower():
            return c
    raise KeyError(f"no column containing {needle!r} in {list(df.columns)}")


def _add_date(df):
    """Build a month-start date column from the year and month-name columns."""
    y, m = _col(df, "year"), _col(df, "month")
    df["date"] = pd.to_datetime({
        "year": df[y].astype(int),
        "month": df[m].map(_MONTHS),
        "day": 1,
    })
    return df


def fetch_monthly_prices() -> pd.DataFrame:
    """Farm-gate prices, EUR, for 32 products. Columns: product, date, price."""
    df = _add_date(_fetch_full(_OUTPUT_NODE + ["ICPB04.px"]))
    out = df.rename(columns={_col(df, "output"): "product", "value": "price"})
    out = out[["product", "date", "price"]].dropna(subset=["price"])
    return out.sort_values(["product", "date"]).reset_index(drop=True)


def fetch_output_index() -> pd.DataFrame:
    """Total agricultural output price index, monthly. Columns: date, out_index."""
    df = _add_date(_fetch_full(
        _OUTPUT_NODE + ["ICPB03.px"],
        filters={"Kodi i artikullit/grupet": ["45"]},  # '14 Total Output'
    ))
    out = df.rename(columns={"value": "out_index"})[["date", "out_index"]]
    return out.dropna().sort_values("date").reset_index(drop=True)


def fetch_input_index() -> pd.DataFrame:
    """Total agricultural input price index (2020=100), monthly. Columns: date, in_index."""
    df = _add_date(_fetch_full(
        _INPUT_NODE + ["indeksi-mujore.px"],
        filters={"Kodi  i I\u00c7PB / P\u00ebrshkrimi": ["20"]},  # '220000 INPUT TOTAL'
    ))
    out = df.rename(columns={"value": "in_index"})[["date", "in_index"]]
    return out.dropna().sort_values("date").reset_index(drop=True)
