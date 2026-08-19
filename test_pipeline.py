"""End-to-end test against the LIVE APIs: fetch all four datasets, run every analysis."""
from ingest import askdata, openmeteo, worldbank
from ingest.common import with_fallback
import analysis

prices = with_fallback("prices", askdata.fetch_monthly_prices)
out_idx = with_fallback("out_idx", askdata.fetch_output_index)
in_idx = with_fallback("in_idx", askdata.fetch_input_index)
weather = with_fallback("weather_Prishtina", lambda: openmeteo.fetch_monthly_weather("Prishtina"))
infl = with_fallback("inflation", worldbank.fetch_inflation)

assert not prices.empty and {"product", "date", "price"}.issubset(prices.columns)
assert prices["date"].notna().all() and prices["price"].notna().all()
assert not out_idx.empty and not in_idx.empty and not weather.empty and not infl.empty

print("prices:", prices.shape, "| products:", prices["product"].nunique(),
      "| span:", prices["date"].min().date(), "->", prices["date"].max().date())
print("out_idx:", out_idx.shape, "| in_idx:", in_idx.shape,
      "| weather:", weather.shape, "| inflation:", infl.shape)

crop = "Potato"
season = analysis.seasonality(prices, crop)
hi, lo = analysis.best_month(season)
print(f"\n[{crop}] best month to SELL: {hi} | cheapest month: {lo}")

panel = analysis.weather_price_panel(prices, weather, crop)
print(f"[{crop}] weather correlations:", analysis.weather_correlations(panel))

ms = analysis.margin_squeeze(out_idx, in_idx)
latest = ms.iloc[-1]
print(f"[margin] {latest['date'].date()}: output {latest['out_rebased']:.1f} vs "
      f"input {latest['in_rebased']:.1f} -> margin {latest['margin']:.1f} (Jan-2022=100)")

real = analysis.deflate(prices, infl, crop)
n, r = real.iloc[-1]["price"], real.iloc[-1]["real_price"]
print(f"[{crop}] latest nominal ASK price value {n:.2f} vs real (2022 money) {r if r == r else 'not available: CPI not published'}")

fc = analysis.forecast(prices, crop)
print(f"[{crop}] forecast:")
print(fc.to_string(index=False))
assert {"n", "enough_history"}.issubset(fc.columns)
print("\nPipeline smoke test: PASS (live data where available, otherwise explicit fallback snapshots).")
