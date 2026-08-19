# Data sources and provenance

## Retrieval policy

The app requests public APIs first. On failure, `ingest.common.load_with_fallback` loads the matching bundled `data/fallback/*.parquet` snapshot and labels it `FALLBACK`. Normal app runs never write snapshots. `python scripts/validate_sources.py` prints live ASK metadata where available.

## ASKdata farm-gate prices

- **Dataset:** `ICPB04.px`; endpoint: `ingest.askdata.table_url("prices")`.
- **Provider/path:** Kosovo Agency of Statistics ASKdata → Agriculture → Agriculture Price and Price Index → Output Price Index and Prices in Agriculture.
- **Grain/fields:** monthly ASK product dimension; source year/month becomes `date`, returned value becomes `price`.
- **Bundled coverage:** Jan 2022–Jun 2026, 32 product labels (dynamic in UI/report).
- **Use/join:** product history, seasonality, baseline, annual-CPI deflation, joined to weather on month-start `date`.
- **Units:** must be confirmed from current ASK metadata before product-specific presentation; the app does not infer common physical units across products.
- **Limitation:** national data and legitimate seasonal gaps.

## ASKdata output and input indices

- **Datasets:** `ICPB03.px` (`ingest.askdata.table_url("output_index")`) and `indeksi-mujore.px` (`ingest.askdata.table_url("input_index")`).
- **Live metadata verified 19 Aug 2026:** output code `Kodi i artikullit/grupet = "45"` is labelled `14 Total Output`; input code `Kodi  i IÇPB / Përshkrimi = "20"` is labelled `220000 INPUT TOTAL (INPUT 1 + INPUT 2)`. The validation script prints these labels and warns if a code is absent.
- **Grain/coverage:** monthly; bundled snapshots cover Jan 2015–Jun 2026.
- **Use/join:** inner join on `date`; indices rebased to Jan 2022 = 100; `output_rebased / input_rebased * 100` is the Kosovo-wide price-cost index ratio proxy.
- **Limitation:** not a crop-specific or farm-specific margin; it excludes yield, labour, land, storage, and farm input mix.

## Open-Meteo Archive weather

- **Endpoint:** `https://archive-api.open-meteo.com/v1/archive`.
- **Grain:** daily precipitation sum and mean temperature aggregated to month-start `date`, `rain_mm`, and `temp_c`.
- **Selection:** region coordinates are in `ingest/openmeteo.py`; only regions with bundled snapshot files are selectable, guaranteeing offline operation.
- **Use/join:** joins national price by month; one/two-month lags are used in exploratory Pearson correlations.
- **Units:** millimetres and °C.
- **Limitation:** city weather is not Kosovo-wide; correlation is descriptive, not causal or predictive.

## World Bank Kosovo CPI

- **Endpoint:** World Bank country `XKX`, indicator `FP.CPI.TOTL.ZG`.
- **Grain/fields:** annual inflation percentage; `year`, `inflation_pct`.
- **Bundled coverage:** 2003–2025 at review time (dynamic in app/report).
- **Use/join:** monthly price maps to calendar year for approximate 2022-money comparison.
- **Limitation:** annual CPI is coarse for monthly prices. No real price is calculated after the latest published CPI year.

## Derived metrics

| Metric | Formula/grain | Interpretation |
|---|---|---|
| Seasonal average | Mean price grouped by calendar month, with `n` | Historical selling-timing context. |
| Seasonal baseline | Same-month historic mean ± one SD, minimum three observations | Explainable baseline, not trained forecast. |
| Backtest MAE | Rolling one-step error using earlier same-month data | Basic accuracy indicator. |
| Price-cost ratio | Rebased output/input indices | Kosovo-wide proxy, not farm profit. |
| Weather correlation | Pearson price vs weather/lags after month join | Exploratory association only. |
| Real price | Nominal price divided by annual CPI level | Only published-CPI years; approximate. |
