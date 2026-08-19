"""Keshilltari i Fermerit - a data app for a Kosovar farmer deciding
what to plant and when to sell. All data is about Kosovo, fetched live:
ASKdata (prices + input costs), Open-Meteo (weather at Kosovo coordinates),
World Bank (Kosovo XKX inflation)."""
import os

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

import ai
import analysis
from ingest import askdata, openmeteo, worldbank
from ingest.common import with_fallback

st.set_page_config(page_title="Keshilltari i Fermerit", page_icon="🌾", layout="wide")


# ---- cached live loaders (automation: live API + 1h cache + parquet fallback) ----

@st.cache_data(ttl=3600, show_spinner="Duke marre cmimet nga ASK... / fetching prices...")
def load_prices():
    return with_fallback("prices", askdata.fetch_monthly_prices)

@st.cache_data(ttl=3600, show_spinner=False)
def load_out_idx():
    return with_fallback("out_idx", askdata.fetch_output_index)

@st.cache_data(ttl=3600, show_spinner=False)
def load_in_idx():
    return with_fallback("in_idx", askdata.fetch_input_index)

@st.cache_data(ttl=3600, show_spinner="Duke marre motin... / fetching weather...")
def load_weather(region: str):
    return with_fallback(f"weather_{region}", lambda: openmeteo.fetch_monthly_weather(region))

@st.cache_data(ttl=3600, show_spinner=False)
def load_inflation():
    return with_fallback("inflation", worldbank.fetch_inflation)

@st.cache_data(ttl=3600, show_spinner="AI po analizon... / AI is thinking...")
def cached_insight(context: str, _key):
    return ai.generate_insight(context, _key)


def api_key():
    try:
        return st.secrets["ANTHROPIC_API_KEY"]
    except Exception:
        return os.environ.get("ANTHROPIC_API_KEY")


# ---- data ----

prices = load_prices()
out_idx = load_out_idx()
in_idx = load_in_idx()
inflation = load_inflation()

st.sidebar.title("🌾 Keshilltari i Fermerit")
st.sidebar.caption("Built for: a Kosovar farmer deciding **what to plant** "
                   "and **when to sell**. / Per fermerin qe vendos cka te mbjelle "
                   "e kur te shese.")
products = sorted(prices["product"].unique())
crop = st.sidebar.selectbox("Produkti / Crop", products,
                            index=products.index("Potato") if "Potato" in products else 0)
region = st.sidebar.selectbox("Regjioni / Your region", list(openmeteo.REGIONS))
weather = load_weather(region)

latest_date = prices["date"].max()
st.sidebar.caption(f"📡 Live APIs, cached 1h. Latest ASK price month: "
                   f"**{latest_date:%B %Y}**. All data is about Kosovo 🇽🇰")
with st.sidebar.expander("Burimet / Data sources"):
    st.markdown(
        "- **ASKdata** - monthly farm-gate prices (ICPB04) and the output (ICPB03) "
        "& input price indices, Kosovo Agency of Statistics\n"
        "- **Open-Meteo** - monthly weather history at your region's coordinates\n"
        "- **World Bank** - Kosovo (XKX) CPI inflation, used to compute real prices"
    )

# ---- header + headline metrics ----

st.title(f"{crop} - a po ia vlen sivjet? / Is it worth it this year?")

series = prices[prices["product"] == crop].sort_values("date")
season = analysis.seasonality(prices, crop)
hi_month, lo_month = analysis.best_month(season)
now = series.iloc[-1]
prev = series.iloc[-2] if len(series) > 1 else now
yoy = series[series["date"] == now["date"] - pd.DateOffset(years=1)]

c1, c2, c3, c4 = st.columns(4)
c1.metric(f"Cmimi {now['date']:%b %Y} / price", f"{now['price']:.2f} EUR",
          f"{now['price'] - prev['price']:+.2f} vs muajin e kaluar")
c2.metric("Nje vit me pare / a year ago",
          f"{float(yoy['price'].iloc[0]):.2f} EUR" if len(yoy) else "n/a",
          f"{now['price'] - float(yoy['price'].iloc[0]):+.2f}" if len(yoy) else None)
c3.metric("Muaji me i mire per shitje / best month to sell", hi_month)
c4.metric("Muaji me i lire / cheapest month", lo_month)

# ---- AI insight (rubric: in-app LLM summary + anomaly flag) ----

ms = analysis.margin_squeeze(out_idx, in_idx)
panel = analysis.weather_price_panel(prices, weather, crop)
corrs = analysis.weather_correlations(panel)
real = analysis.deflate(prices, inflation, crop)
this_month_norm = season[season["month"] == now["date"].month]["avg"].iloc[0]

context = (
    f"crop={crop}; latest_price_eur={now['price']:.2f} ({now['date']:%Y-%m}); "
    f"seasonal_norm_for_this_calendar_month={this_month_norm:.2f}; "
    f"best_month_to_sell={hi_month}; cheapest_month={lo_month}; "
    f"margin_index_now={ms.iloc[-1]['margin']:.1f} (Jan2022=100, >100 means prices beat input costs); "
    f"weather_price_correlations={corrs} (region={region}); "
    f"latest_real_price_2022_money={real.iloc[-1]['real_price']:.2f}"
)
if st.button("🤖 Analiza AI / AI insight"):
    text = cached_insight(context, api_key())
    if text:
        st.info(text)
    else:
        st.warning("Add ANTHROPIC_API_KEY to .streamlit/secrets.toml to enable AI insights. "
                   "The aggregated context the model would receive is shown below.")
        st.code(context)

# ---- tabs: the four analyses ----

t1, t2, t3, t4 = st.tabs(["📅 Kur te shes? / When to sell",
                          "🌦️ Moti & cmimet / Weather vs price",
                          "⚖️ Kostot / Costs vs prices",
                          "💶 Cmimet reale / Real prices"])

with t1:
    left, right = st.columns(2)
    with left:
        st.subheader("Sezonaliteti / Seasonal pattern")
        fig = px.bar(season, x="month_name", y="avg",
                     labels={"month_name": "", "avg": "avg price (EUR)"},
                     color=season["month_name"].eq(hi_month),
                     color_discrete_map={True: "#1D9E75", False: "#B4B2A9"})
        fig.update_layout(showlegend=False, height=360)
        st.plotly_chart(fig, width="stretch")
        st.success(f"Mesatarisht, **{crop}** shitet me se shtrenjti ne **{hi_month}** "
                   f"dhe me se liri ne **{lo_month}**. / On average, {crop} sells "
                   f"highest in {hi_month} and lowest in {lo_month}.")
    with right:
        st.subheader("Parashikimi 3-mujor / 3-month forecast")
        fc = analysis.forecast(prices, crop)
        hist = series.tail(24)
        fig = go.Figure()
        fig.add_scatter(x=hist["date"], y=hist["price"], name="historia / history")
        fig.add_scatter(x=fc["date"], y=fc["hi"], line=dict(width=0), showlegend=False)
        fig.add_scatter(x=fc["date"], y=fc["lo"], fill="tonexty", line=dict(width=0),
                        name="±1 std", fillcolor="rgba(29,158,117,0.2)")
        fig.add_scatter(x=fc["date"], y=fc["forecast"], mode="lines+markers",
                        name="parashikimi / forecast", line=dict(dash="dash", color="#1D9E75"))
        fig.update_layout(height=360, yaxis_title="EUR",
                          legend=dict(orientation="h", y=1.1))
        st.plotly_chart(fig, width="stretch")
        st.caption("Metoda: mesatarja e te njejtit muaj neper vite ±1 devijim standard - "
                   "e thjeshte dhe e shpjegueshme. / Method: same-calendar-month average "
                   "across years ±1 std - simple and explainable.")

with t2:
    st.subheader(f"A ndikon moti i {region}-s ne cmimin e {crop}? / "
                 f"Does {region}'s weather move the price?")
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_scatter(x=panel["date"], y=panel["price"], name=f"{crop} EUR")
    fig.add_bar(x=panel["date"], y=panel["rain_mm"], name="shiu / rain (mm)",
                opacity=0.4, marker_color="#378ADD", secondary_y=True)
    fig.update_layout(height=380, legend=dict(orientation="h", y=1.1))
    fig.update_yaxes(title_text="EUR", secondary_y=False)
    fig.update_yaxes(title_text="mm", secondary_y=True)
    st.plotly_chart(fig, width="stretch")
    cc = st.columns(3)
    cc[0].metric("korrelacioni shi->cmim (i njejti muaj)", corrs["rain_mm"])
    cc[1].metric("shiu 1 muaj perpara / rain 1 month earlier", corrs["rain_lag1"])
    cc[2].metric("temperatura 2 muaj perpara / temp 2 months earlier", corrs["temp_lag2"])
    st.caption("Kujdes: korrelacioni nuk eshte shkak-pasoje; cmimet e ASK jane kombetare, "
               "moti eshte i regjionit tend. / Note: correlation is not causation; ASK "
               "prices are national while weather is your region's.")

with t3:
    st.subheader("Cmimet e produkteve vs kostot e inputeve / Output prices vs input costs")
    fig = go.Figure()
    fig.add_scatter(x=ms["date"], y=ms["out_rebased"], name="cmimet e prodhimit / output prices")
    fig.add_scatter(x=ms["date"], y=ms["in_rebased"], name="kostot e inputeve / input costs")
    fig.add_scatter(x=ms["date"], y=ms["margin"], name="marzha / margin",
                    line=dict(dash="dot", color="#D85A30"))
    fig.add_hline(y=100, line_dash="dash", line_color="gray")
    fig.update_layout(height=380, yaxis_title="index, Jan 2022 = 100",
                      legend=dict(orientation="h", y=1.1))
    st.plotly_chart(fig, width="stretch")
    m = ms.iloc[-1]["margin"]
    verdict = ("cmimet kane rritur me shume se kostot - marzhat me te mira" if m > 100
               else "kostot po rriten me shpejt se cmimet - marzhat nen presion")
    st.success(f"Marzha tani: **{m:.1f}** (Jan 2022 = 100) - {verdict}. / Margin now "
               f"{m:.1f}: {'prices have outrun input costs' if m > 100 else 'input costs are outrunning prices'} "
               f"since Jan 2022.")

with t4:
    st.subheader("Nominal vs real (parate e 2022-es) / in 2022 money")
    fig = go.Figure()
    fig.add_scatter(x=real["date"], y=real["price"], name="nominal EUR")
    fig.add_scatter(x=real["date"], y=real["real_price"], name="real EUR (2022)",
                    line=dict(color="#534AB7"))
    fig.update_layout(height=380, yaxis_title="EUR", legend=dict(orientation="h", y=1.1))
    st.plotly_chart(fig, width="stretch")
    st.caption("Deflatuar me inflacionin e Kosoves (World Bank, XKX). / Deflated with "
               "Kosovo's own CPI (World Bank, country code XKX).")

st.divider()
st.caption("Te dhenat: ASKdata (Agjencia e Statistikave te Kosoves), Open-Meteo, "
           "World Bank - te gjitha per Kosoven 🇽🇰, te marra live permes API-ve dhe "
           "te ruajtura 1 ore ne cache, me kopje rezerve parquet nese nje API bie.")
