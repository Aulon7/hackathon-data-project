# 🌾 Këshilltari i Fermerit — Kosovo Farmer's Price Advisor

A Streamlit decision-support app for a Kosovar farmer deciding **when to consider selling a selected product**. It does not recommend what to plant or calculate farm profit: crop-specific yield, costs, storage, and suitability data are not included.

## What it does

- Shows national ASKdata product-price seasonality with observation counts.
- Provides a three-month **seasonal baseline** with a minimum-history rule and rolling backtest MAE.
- Combines national prices and selected-city weather as exploratory correlations only.
- Shows a national agricultural **price-cost index ratio proxy**, not a farm profit margin.
- Shows annual-CPI-adjusted prices only through the latest published Kosovo CPI year.
- Provides an optional Anthropic AI insight or an honest rule-based fallback summary.

## Setup and verification

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m pytest -q
python scripts/validate_sources.py
python test_pipeline.py
streamlit run app.py
```

## Data and availability

The app is live-first: it requests public APIs and falls back to bundled Parquet snapshots when a source is unavailable. Normal app runs never overwrite snapshots. The UI labels data `LIVE` or `FALLBACK` and displays coverage.

| Dataset | Provider | Use |
|---|---|---|
| Farm-gate prices (`ICPB04.px`) | ASKdata | Product history, seasonality, baseline. |
| Output/input indices (`ICPB03.px`, `indeksi-mujore.px`) | ASKdata | National price-cost proxy. |
| Regional weather | Open-Meteo Archive | Exploratory weather/price panel. |
| Kosovo CPI (`XKX`, `FP.CPI.TOTL.ZG`) | World Bank | Annual-frequency real-price approximation. |

See [docs/data_sources.md](docs/data_sources.md) for endpoint, grain, unit, join, and limitation details.

## Optional AI insight

Create `.streamlit/secrets.toml` (never commit it):

```toml
ANTHROPIC_API_KEY = "your-key"
```

The LLM receives aggregate values only and is instructed not to make causal, planting, or profit claims. Without a key, the app displays a clearly labelled rule-based summary.

## Important limitations

- ASK prices are national; weather is a selected city coordinate. Correlation does not establish causation.
- The seasonal baseline is not a trained forecast and can be weak for sparse seasonal products.
- The index ratio is national and aggregate, not a crop/farm margin.
- Annual CPI is a coarse deflator for monthly prices; later dates remain blank until CPI is published.
- Verify ASK product units and definitions with `python scripts/validate_sources.py` before making a product-specific public claim.
