"""Kosovo Farmer's Price Advisor: evidence for selling timing, not crop choice."""
import os
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

import ai
import analysis
from ingest import askdata, openmeteo, worldbank
from ingest.common import load_with_fallback

st.set_page_config(page_title="Kosovo Farmer's Price Advisor", page_icon="🌾", layout="wide")

# New visitors begin with the contextual About page; its CTA opens this advisor.
if not st.session_state.get("advisor_opened", False):
    st.switch_page("pages/1_About.py")

# The advisor uses its own sidebar controls rather than Streamlit's page list.
st.markdown("<style>[data-testid='stSidebarNav'] {display: none !important;}</style>", unsafe_allow_html=True)

SOURCES = {
    "prices": "ASKdata / ICPB04.px — monthly farm-gate prices",
    "out_idx": "ASKdata / ICPB03.px — agricultural output price index",
    "in_idx": "ASKdata / indeksi-mujore.px — agricultural input price index",
    "weather": "Open-Meteo Archive — monthly weather at selected city coordinate",
    "inflation": "World Bank XKX / FP.CPI.TOTL.ZG — annual CPI inflation",
}


@st.cache_data(ttl=3600, show_spinner="Fetching ASK farm-gate prices…")
def load_prices(): return load_with_fallback("prices", askdata.fetch_monthly_prices, SOURCES["prices"])
@st.cache_data(ttl=3600, show_spinner=False)
def load_out_idx(): return load_with_fallback("out_idx", askdata.fetch_output_index, SOURCES["out_idx"])
@st.cache_data(ttl=3600, show_spinner=False)
def load_in_idx(): return load_with_fallback("in_idx", askdata.fetch_input_index, SOURCES["in_idx"])
@st.cache_data(ttl=3600, show_spinner="Fetching regional weather…")
def load_weather(region): return load_with_fallback(f"weather_{region}", lambda: openmeteo.fetch_monthly_weather(region), SOURCES["weather"])
@st.cache_data(ttl=3600, show_spinner=False)
def load_inflation(): return load_with_fallback("inflation", worldbank.fetch_inflation, SOURCES["inflation"])
@st.cache_data(ttl=3600, show_spinner="Preparing AI insight…")
def cached_insight(context, key): return ai.generate_insight(context, key)


def api_key():
    try: return st.secrets["ANTHROPIC_API_KEY"]
    except Exception: return os.environ.get("ANTHROPIC_API_KEY")


def show_status(name, result, unit):
    st.write(f"**{name}:** {result.status.upper()} · {result.coverage.replace(' 00:00:00', '')} · {unit}")


prices_result, out_result, in_result, inflation_result = load_prices(), load_out_idx(), load_in_idx(), load_inflation()
prices, out_idx, in_idx, inflation = prices_result.data, out_result.data, in_result.data, inflation_result.data
safe_regions = openmeteo.fallback_regions()
if not safe_regions:
    st.error("No bundled weather fallback is available. Restore data/fallback/weather_*.parquet.")
    st.stop()

st.sidebar.title("🌾 Kosovo Farmer's Price Advisor")
st.sidebar.caption("For a Kosovar farmer deciding when to sell a selected product.")
products = sorted(prices["product"].unique())
crop = st.sidebar.selectbox("Product", products, index=products.index("Potato") if "Potato" in products else 0)
region = st.sidebar.selectbox("Weather region", safe_regions)
weather_result = load_weather(region)
weather = weather_result.data
st.sidebar.caption("Only regions with bundled weather snapshots are shown so the app also works offline.")
with st.sidebar.expander("Data status"):
    show_status("Farm-gate prices", prices_result, "unit: verify in ASK metadata")
    show_status("Output index", out_result, "index")
    show_status("Input index", in_result, "index")
    show_status(f"Weather ({region})", weather_result, "mm and °C")
    show_status("CPI inflation", inflation_result, "% per year")
    st.caption("LIVE = fetched this session; FALLBACK = bundled snapshot. Retrieved (UTC): " + prices_result.retrieved_at)

st.sidebar.divider()
if st.sidebar.button("Return to About page", icon="ℹ️", use_container_width=True):
    st.session_state["advisor_opened"] = False
    st.switch_page("pages/1_About.py")

series = prices[prices["product"] == crop].sort_values("date")
season = analysis.seasonality(prices, crop)
hi_month, lo_month = analysis.best_month(season)
now, prev = series.iloc[-1], series.iloc[-2] if len(series) > 1 else series.iloc[-1]
yoy = series[series["date"] == now["date"] - pd.DateOffset(years=1)]
ms = analysis.margin_squeeze(out_idx, in_idx)
panel = analysis.weather_price_panel(prices, weather, crop)
corrs = analysis.weather_correlations(panel)
real = analysis.deflate(prices, inflation, crop)
fc, backtest = analysis.forecast(prices, crop), analysis.forecast_backtest(prices, crop)
month_row = season[season["month"] == now["date"].month].iloc[0]

st.title(f"{crop}: when should I consider selling?")
st.caption(f"National ASK farm-gate prices through {now['date']:%B %Y}. This app supports selling timing, not a crop-profitability recommendation.")
c1, c2, c3, c4 = st.columns(4)
c1.metric(f"ASK price value ({now['date']:%b %Y})", f"{now['price']:.2f}", f"{now['price'] - prev['price']:+.2f} vs prior month")
c2.metric("Same month one year ago", f"{float(yoy['price'].iloc[0]):.2f}" if len(yoy) else "n/a")
c3.metric("Historical highest-average month", hi_month)
c4.metric("Historical lowest-average month", lo_month)
st.caption("Product unit and definition are supplied by ASKdata metadata; verify them with `python scripts/validate_sources.py` before presenting a product-specific claim.")

context = (f"selected product={crop}; national ASK price value={now['price']:.2f} in {now['date']:%Y-%m}; "
           f"same-calendar-month historical mean price value={month_row['avg']:.2f} based on n={int(month_row['n'])}; "
           f"historical high-average month={hi_month}; low-average month={lo_month}; "
           f"agricultural price-cost index ratio={ms.iloc[-1]['margin']:.1f} in {ms.iloc[-1]['date']:%Y-%m}; "
           f"weather-price correlations={corrs}, n_matched_months={len(panel)}, weather_region={region}; "
           f"real price available through {real.loc[real['cpi_available'], 'date'].max():%Y-%m} using annual CPI")
if st.button("🤖 AI insight"):
    insight = cached_insight(context, api_key())
    if insight: st.info(insight)
    else:
        st.info(ai.rule_based_summary(crop, now, month_row, hi_month, ms.iloc[-1], len(panel)))
        st.caption("Rule-based fallback: no Anthropic API key or the AI request was unavailable.")

t1, t2, t3, t4 = st.tabs(["📅 Selling timing", "🌦️ Weather context", "⚖️ Price-cost context", "💶 Real prices"])
with t1:
    left, right = st.columns(2)
    with left:
        plot = season.copy(); plot["label"] = plot.apply(lambda r: f"{r['month_name']} (n={int(r['n'])})", axis=1)
        fig = px.bar(plot, x="label", y="avg", labels={"label": "", "avg": "average ASK price value"}, color=plot["month_name"].eq(hi_month), color_discrete_map={True: "#1D9E75", False: "#B4B2A9"})
        fig.update_layout(showlegend=False, height=360); st.plotly_chart(fig, width="stretch")
        st.success(f"Historical average is highest in **{hi_month}** and lowest in **{lo_month}**. Missing months are not imputed.")
    with right:
        valid_fc = fc[fc["enough_history"]]; fig = go.Figure(); hist = series.tail(24)
        fig.add_scatter(x=hist["date"], y=hist["price"], name="history")
        if not valid_fc.empty:
            fig.add_scatter(x=valid_fc["date"], y=valid_fc["hi"], line=dict(width=0), showlegend=False)
            fig.add_scatter(x=valid_fc["date"], y=valid_fc["lo"], fill="tonexty", line=dict(width=0), name="historical variability band", fillcolor="rgba(29,158,117,0.2)")
            fig.add_scatter(x=valid_fc["date"], y=valid_fc["forecast"], mode="lines+markers", name="seasonal baseline", line=dict(dash="dash", color="#1D9E75"))
        fig.update_layout(height=360, yaxis_title="ASK price-value units", legend=dict(orientation="h", y=1.1)); st.plotly_chart(fig, width="stretch")
        st.caption("Seasonal baseline = historical same-calendar-month average ± one standard deviation; it is not a trained predictive model.")
        if fc["enough_history"].all(): st.caption(f"Forecast n: {', '.join(str(int(n)) for n in fc['n'])}. Rolling one-step backtest: n={backtest['n']}, MAE={backtest['mae'] if backtest['mae'] is not None else 'n/a'} price-value units.")
        else: st.warning("One or more forecast months have fewer than three historical observations, so no precise baseline is shown.")
with t2:
    st.subheader(f"Weather context for {region} and national {crop} price")
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_scatter(x=panel["date"], y=panel["price"], name=f"{crop} price"); fig.add_bar(x=panel["date"], y=panel["rain_mm"], name="rain (mm)", opacity=0.4, marker_color="#378ADD", secondary_y=True)
    fig.update_layout(height=380, legend=dict(orientation="h", y=1.1)); fig.update_yaxes(title_text="ASK price value", secondary_y=False); fig.update_yaxes(title_text="rain (mm)", secondary_y=True); st.plotly_chart(fig, width="stretch")
    cc = st.columns(3); cc[0].metric("Same-month rain correlation", corrs["rain_mm"]); cc[1].metric("Rain one month earlier", corrs["rain_lag1"]); cc[2].metric("Temperature two months earlier", corrs["temp_lag2"])
    st.caption(f"Matched months: {len(panel)} ({panel['date'].min():%Y-%m}–{panel['date'].max():%Y-%m}). Exploratory only: ASK prices are national and weather comes from a {region} city coordinate; correlation does not establish causation.")
with t3:
    st.subheader("Kosovo-wide agricultural price-cost index ratio (proxy)")
    fig = go.Figure(); fig.add_scatter(x=ms["date"], y=ms["out_rebased"], name="output price index"); fig.add_scatter(x=ms["date"], y=ms["in_rebased"], name="input price index"); fig.add_scatter(x=ms["date"], y=ms["margin"], name="price-cost index ratio", line=dict(dash="dot", color="#D85A30")); fig.add_hline(y=100, line_dash="dash", line_color="gray")
    fig.update_layout(height=380, yaxis_title="index, Jan 2022 = 100", legend=dict(orientation="h", y=1.1)); st.plotly_chart(fig, width="stretch")
    st.info(f"Latest ratio: **{ms.iloc[-1]['margin']:.1f}** in {ms.iloc[-1]['date']:%B %Y}. Above 100 means national output prices rose faster than national input prices since Jan 2022; it is not this crop's or this farm's profit margin.")
with t4:
    st.subheader("Nominal vs real ASK price value (2022 money, annual CPI approximation)")
    fig = go.Figure(); fig.add_scatter(x=real["date"], y=real["price"], name="nominal ASK price value"); fig.add_scatter(x=real["date"], y=real["real_price"], name="real price value (2022 money)", line=dict(color="#534AB7")); fig.update_layout(height=380, yaxis_title="ASK price-value units", legend=dict(orientation="h", y=1.1)); st.plotly_chart(fig, width="stretch")
    last_real = real.loc[real["cpi_available"], "date"].max()
    st.caption(f"Uses Kosovo annual CPI inflation from the World Bank. Real-price values are only shown through {last_real:%B %Y}; later months are blank until published CPI exists. Annual CPI is a coarse approximation for monthly prices.")
st.divider(); st.caption("Sources: ASKdata (Kosovo Agency of Statistics), Open-Meteo Archive, and World Bank XKX. See docs/data_sources.md and scripts/validate_sources.py.")
