# 🌾 Keshilltari i Fermerit — Farmer's Price Advisor (Kosovo)

A data app for **one person**: a Kosovar farmer deciding *what to plant* and *when to sell*.
Built for the MICP Data Science hackathon. Every dataset is about Kosovo and every dataset
enters the app through a **live API** — no CSV uploads.

## Quickstart

    pip install -r requirements.txt
    streamlit run app.py

First load fetches everything live (~20s), then it's cached for 1 hour.
`python test_pipeline.py` runs the whole ingest + analysis pipeline headless.

**AI insights (optional):** create `.streamlit/secrets.toml` with

    ANTHROPIC_API_KEY = "sk-ant-..."

Without a key the app still works and shows the aggregated context it would send.

## Deploy (free)

Push this folder to GitHub → share.streamlit.io → New app → pick the repo, main file
`app.py` → add `ANTHROPIC_API_KEY` under app **Settings → Secrets** → Deploy.
You get a public URL for the judges.

## Data (all Kosovo, all live APIs)

| Dataset | Source | Table / series | Join key |
|---|---|---|---|
| Farm-gate prices, 32 products, monthly 2022→ | ASKdata (PxWeb API) | `ICPB04.px` | month |
| Output price index, monthly 2015→ | ASKdata | `ICPB03.px`, category "Total Output" | month |
| Input price index (2020=100), monthly 2015→ | ASKdata | `indeksi-mujore.px`, "INPUT TOTAL" | month |
| Weather (rain, temperature) at your region | Open-Meteo archive | daily → aggregated monthly | month |
| Kosovo CPI inflation | World Bank, country **XKX** | `FP.CPI.TOTL.ZG` | year |

## How the sources are *genuinely combined*

- **Seasonality + forecast** (trend): best/cheapest month per crop; next 3 months as
  same-calendar-month average ± 1 std.
- **Weather → price** (correlation): your region's rain/temperature vs national prices,
  at 0–2 month lags. The app says out loud that correlation ≠ causation.
- **Margin squeeze** (comparison): output vs input index, both rebased to Jan 2022 = 100.
  As of mid-2026: output ≈ 144 vs input ≈ 124 → margin ≈ 117, i.e. prices have outrun costs.
- **Real prices**: nominal EUR deflated by Kosovo's own CPI into 2022 money.
- **AI insight**: one LLM call on the aggregated numbers → 3 plain sentences (SQ + EN)
  incl. an anomaly flag.

## Resilience

Every fetch is wrapped in `with_fallback`: live API first, snapshot to
`data/fallback/*.parquet` on success, load the snapshot if the API is down.
The shipped snapshots mean the demo works even on dead wifi — but by default it is live.

## Structure

    app.py             Streamlit UI (persona header, metrics, AI insight, 4 tabs)
    analysis.py        seasonality, correlations, margin squeeze, deflation, forecast
    ai.py              LLM insight on aggregated data (anthropic, optional)
    ingest/askdata.py  PxWeb client for the 3 ASK tables (all quirks documented inline)
    ingest/openmeteo.py, ingest/worldbank.py, ingest/common.py (retry + fallback)
    test_pipeline.py   headless end-to-end test against the live APIs

## Known limits (say these to the judges before they ask)

- ASK prices are **national**, weather is **regional** — the correlation view is indicative.
- The forecast is a seasonal average, chosen for explainability over sophistication.
- ASK publishes prices with ~1–2 months lag; the app shows the latest month automatically.
