"""Validate source availability, metadata, and data quality without Streamlit.

Run: python scripts/validate_sources.py
The report remains useful offline because every data fetch has an explicit fallback.
"""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ingest import askdata, openmeteo, worldbank
from ingest.common import load_with_fallback


def check_frame(name, result, date_column):
    df = result.data
    duplicates = int(df.duplicated().sum())
    nulls = int(df.isna().sum().sum())
    print(f"{name}: {result.status.upper()} | rows={len(df)} | coverage={result.coverage} | null cells={nulls} | duplicate rows={duplicates}")
    if date_column in df and not df[date_column].is_monotonic_increasing:
        print("  Note: rows are not globally date-sorted (expected for product-level price data).")


def metadata_report(table_name, selected_code=None):
    print(f"\nASKdata {table_name}: {askdata.table_url(table_name)}")
    try:
        metadata = askdata.fetch_metadata(table_name)
    except Exception as exc:
        print(f"  metadata: UNAVAILABLE ({exc})")
        return
    print("  metadata: LIVE OK")
    for variable in metadata.get("variables", []):
        values = variable.get("values", [])
        labels = variable.get("valueTexts", [])
        selected = ""
        if selected_code and variable.get("code") == selected_code[0]:
            try:
                index = values.index(selected_code[1])
                selected = f"; selected={selected_code[1]!r} / {labels[index]!r}"
            except ValueError:
                selected = f"; WARNING selected code {selected_code[1]!r} absent"
        print(f"  dimension {variable.get('code')!r}: {variable.get('text')!r}; values={len(values)}{selected}")


def main():
    print("Kosovo Farmer Price Advisor — source validation")
    print("Snapshots are used only when a live request fails; no snapshot is overwritten by this script.\n")
    metadata_report("prices")
    metadata_report("output_index", ("Kodi i artikullit/grupet", "45"))
    metadata_report("input_index", ("Kodi  i IÇPB / Përshkrimi", "20"))

    prices = load_with_fallback("prices", askdata.fetch_monthly_prices, askdata.table_url("prices"))
    output = load_with_fallback("out_idx", askdata.fetch_output_index, askdata.table_url("output_index"))
    inputs = load_with_fallback("in_idx", askdata.fetch_input_index, askdata.table_url("input_index"))
    weather = load_with_fallback("weather_Prishtina", lambda: openmeteo.fetch_monthly_weather("Prishtina"), openmeteo.ARCHIVE_URL)
    inflation = load_with_fallback("inflation", worldbank.fetch_inflation, worldbank.WB_URL.format(code="FP.CPI.TOTL.ZG"))
    print("\nData checks")
    check_frame("Farm-gate prices", prices, "date")
    print(f"  products={prices.data['product'].nunique()}")
    check_frame("Output index", output, "date")
    check_frame("Input index", inputs, "date")
    check_frame("Prishtina weather", weather, "date")
    check_frame("Annual CPI inflation", inflation, "year")
    common = set(prices.data["date"]) & set(weather.data["date"])
    index_common = set(output.data["date"]) & set(inputs.data["date"])
    print(f"\nCommon monthly joins: prices/weather={len(common)}; output/input={len(index_common)}")
    print("Weather fallback regions: " + ", ".join(openmeteo.fallback_regions()))
    print("Units: weather precipitation=mm and temperature=°C; CPI=annual percentage. ASK price/index units are printed from live table metadata when supplied by ASKdata.")


if __name__ == "__main__":
    main()
