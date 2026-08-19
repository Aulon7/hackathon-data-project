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
profile = analysis.seasonal_profile(prices, crop)
signal = analysis.selling_signal(now, float(month_row["avg"]), fc)

st.title(f"{crop}: when should I consider selling?")
st.caption(f"National ASK farm-gate prices through {now['date']:%B %Y}. This app supports selling timing, not a crop-profitability recommendation.")
signal_col, c1, c2, c3 = st.columns([1.5, 1, 1, 1])
signal_col.metric("Historical selling signal", signal["label"], signal["reason"])
c1.metric(f"ASK price value ({now['date']:%b %Y})", f"{now['price']:.2f}", f"{now['price'] - prev['price']:+.2f} vs prior month")
c2.metric("Usual value for this month", f"{month_row['avg']:.2f}", f"n={int(month_row['n'])} historical observations")
c3.metric("Historical high-average month", hi_month)
if signal["next_average"] is not None:
    st.caption(f"Next 3-month seasonal baseline average: **{signal['next_average']:.2f}**. This signal is a transparent historical heuristic, not a guarantee; storage, quality, cash needs, and local buyers may change the decision.")

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
    st.subheader("Historical selling calendar")
    fig = go.Figure()
    fig.add_scatter(x=profile["month_name"], y=profile["q75"], line=dict(width=0), showlegend=False, hoverinfo="skip")
    fig.add_scatter(x=profile["month_name"], y=profile["q25"], fill="tonexty", line=dict(width=0), fillcolor="rgba(29, 158, 117, 0.18)", name="middle 50% of observed values", hovertemplate="%{x}<br>Middle 50%: %{y:.2f}<extra></extra>")
    fig.add_scatter(x=profile["month_name"], y=profile["avg"], mode="lines+markers", name="historical average", line=dict(color="#1D9E75", width=3), customdata=profile[["n", "low", "high", "median"]], hovertemplate="%{x}<br>Average: %{y:.2f}<br>Median: %{customdata[3]:.2f}<br>Observed range: %{customdata[1]:.2f}–%{customdata[2]:.2f}<br>Observations: %{customdata[0]}<extra></extra>")
    fig.add_scatter(x=[now["date"].strftime("%B")], y=[now["price"]], mode="markers", name=f"latest ({now['date']:%b %Y})", marker=dict(color="#D85A30", size=13, symbol="diamond"), hovertemplate=f"Latest: {now['price']:.2f}<extra></extra>")
    fig.add_annotation(x=hi_month, y=float(profile.loc[profile["month_name"] == hi_month, "avg"].iloc[0]), text="historical high", showarrow=True, arrowhead=2, yshift=30)
    fig.update_layout(height=410, yaxis_title="ASK price-value units", xaxis_title="Calendar month", legend=dict(orientation="h", y=1.12), margin=dict(t=65))
    st.plotly_chart(fig, width="stretch")
    st.caption("Green line: historical average. Shaded band: middle 50% of observed values. Orange diamond: the latest price, placed in its calendar month. Use the tooltip to see range and observation count.")
    left, right = st.columns(2)
    with left:
        st.subheader("Recent price movement")
        hist = series.tail(30)
        recent = go.Figure()
        recent.add_scatter(x=hist["date"], y=hist["price"], mode="lines+markers", name="observed price", line=dict(color="#378ADD", width=3))
        recent.add_hline(y=float(month_row["avg"]), line_dash="dash", line_color="#1D9E75", annotation_text=f"usual {now['date']:%B} value: {month_row['avg']:.2f}")
        recent.add_scatter(x=[now["date"]], y=[now["price"]], mode="markers", marker=dict(color="#D85A30", size=12), name="latest")
        recent.update_layout(height=330, yaxis_title="ASK price-value units", legend=dict(orientation="h", y=1.12))
        st.plotly_chart(recent, width="stretch")
    with right:
        st.subheader("Next 3 months: seasonal baseline")
        shown_fc = fc.copy(); shown_fc["month"] = shown_fc["date"].dt.strftime("%b %Y")
        st.dataframe(shown_fc[["month", "forecast", "lo", "hi", "n"]].rename(columns={"month": "Month", "forecast": "Baseline", "lo": "Low band", "hi": "High band", "n": "Historical n"}), hide_index=True, width="stretch")
        st.caption("Baseline = same-calendar-month historic average; band = ± one standard deviation. It is not a trained predictive model.")
        if fc["enough_history"].all(): st.caption(f"Rolling one-step backtest: n={backtest['n']}, MAE={backtest['mae'] if backtest['mae'] is not None else 'n/a'} price-value units.")
        else: st.warning("One or more months have fewer than three historical observations, so no precise baseline is shown.")
with t2:
    st.subheader(f"Recent weather context: {region}")
    weather_recent = panel.tail(18)
    relationship = abs(corrs["rain_mm"]) if corrs["rain_mm"] is not None else 0
    relationship_text = "little visible relationship" if relationship < 0.3 else "a possible relationship worth watching"
    a, b, c = st.columns(3)
    a.metric("Latest rainfall", f"{weather_recent.iloc[-1]['rain_mm']:.0f} mm", f"{weather_recent.iloc[-1]['date']:%B %Y}")
    b.metric("Latest temperature", f"{weather_recent.iloc[-1]['temp_c']:.1f} °C")
    c.metric("Weather-price pattern", relationship_text)
    st.info(f"In the available data, rainfall and the national {crop} price show **{relationship_text}**. Use this as local context, not as a prediction or proof of cause.")
    weather_fig = make_subplots(specs=[[{"secondary_y": True}]])
    weather_fig.add_bar(
        x=weather_recent["date"], y=weather_recent["rain_mm"], name=f"rainfall in {region}",
        marker_color="#9EC5FE", opacity=0.55, zorder=0, secondary_y=True,
    )
    weather_fig.add_scatter(
        x=weather_recent["date"], y=weather_recent["price"], mode="lines+markers",
        name=f"national {crop} price", line=dict(color="#087F5B", width=5),
        marker=dict(size=9, color="#087F5B", line=dict(color="white", width=2)),
        zorder=10, secondary_y=False,
    )
    weather_fig.update_layout(
        height=410, title=f"National {crop} price and monthly rainfall in {region}",
        legend=dict(orientation="h", y=1.12), bargap=0.25,
    )
    weather_fig.update_yaxes(title_text="ASK price value", secondary_y=False)
    weather_fig.update_yaxes(title_text="rainfall (mm)", secondary_y=True)
    st.plotly_chart(weather_fig, width="stretch")
    st.caption(f"Green line = national ASK price; blue bars = rainfall in {region}. Both use the same latest 18 matched months. ASK prices are national while weather is measured at a {region} city coordinate; correlation does not establish causation.")
with t3:
    st.subheader("Kosovo-wide agricultural price-cost index ratio (proxy)")
    ratio_col, chart_col = st.columns([1, 2])
    ratio_col.metric("Latest ratio", f"{ms.iloc[-1]['margin']:.1f}", "Jan 2022 = 100")
    ratio_col.caption("Above 100 means the national output-price index has risen faster than the national input-price index since Jan 2022.")
    fig = go.Figure(); fig.add_scatter(x=ms["date"], y=ms["out_rebased"], name="output price index", line=dict(color="#1D9E75", width=3)); fig.add_scatter(x=ms["date"], y=ms["in_rebased"], name="input price index", line=dict(color="#D85A30", width=3)); fig.add_hline(y=100, line_dash="dash", line_color="gray")
    fig.update_layout(height=380, yaxis_title="index, Jan 2022 = 100", legend=dict(orientation="h", y=1.1)); st.plotly_chart(fig, width="stretch")
    st.info(f"Latest ratio: **{ms.iloc[-1]['margin']:.1f}** in {ms.iloc[-1]['date']:%B %Y}. Above 100 means national output prices rose faster than national input prices since Jan 2022; it is not this crop's or this farm's profit margin.")
with t4:
    st.subheader("Nominal vs real ASK price value (2022 money, annual CPI approximation)")
    fig = go.Figure(); fig.add_scatter(x=real["date"], y=real["price"], name="nominal ASK price value"); fig.add_scatter(x=real["date"], y=real["real_price"], name="real price value (2022 money)", line=dict(color="#534AB7")); fig.update_layout(height=380, yaxis_title="ASK price-value units", legend=dict(orientation="h", y=1.1)); st.plotly_chart(fig, width="stretch")
    last_real = real.loc[real["cpi_available"], "date"].max()
    st.caption(f"Uses Kosovo annual CPI inflation from the World Bank. Real-price values are only shown through {last_real:%B %Y}; later months are blank until published CPI exists. Annual CPI is a coarse approximation for monthly prices.")
st.divider(); st.caption("Sources: ASKdata (Kosovo Agency of Statistics), Open-Meteo Archive, and World Bank XKX. See docs/data_sources.md and scripts/validate_sources.py.")
