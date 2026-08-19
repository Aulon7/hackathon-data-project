"""About page for the Kosovo Farmer's Price Advisor."""
import base64
from pathlib import Path

import streamlit as st

st.set_page_config(
    page_title="Rreth aplikacionit | Këshilltari i Fermerit",
    page_icon="ℹ️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
    <style>
      [data-testid="stSidebar"], [data-testid="stSidebarCollapsedControl"] {display: none !important;}
      .hero {padding: 2rem 2.5rem; border-radius: 24px; color: white;
             background: linear-gradient(120deg, #0b5137, #1d9e75 58%, #62b890);
             margin: .4rem 0 2rem 0; display: flex; align-items: center; gap: 2rem;}
      .hero-copy {flex: 1;}
      .hero-qr {width: 155px; min-width: 155px; text-align: center;}
      .hero-qr img {width: 145px; height: 145px; border-radius: 12px; padding: 7px;
                     background: white; display: block; margin: auto;}
      .hero-qr span {display: block; font-size: .8rem; margin-top: .45rem; opacity: .95;}
      .hero h1 {margin: 0 0 .6rem 0; font-size: 2.6rem;}
      .hero p {margin: 0; font-size: 1.12rem; line-height: 1.55; max-width: 760px;}
      .eyebrow {font-size: .84rem; letter-spacing: .08em; font-weight: 700; text-transform: uppercase; opacity: .85;}
      .card {background: #f6fbf8; border: 1px solid #d8eadf; border-radius: 18px;
             padding: 1.35rem; min-height: 155px;}
      .card h3 {color: #0b5137; margin-top: 0;}
      .flow {text-align: center; background: #f6fbf8; border: 1px solid #d8eadf;
             border-radius: 16px; padding: 1rem .6rem; min-height: 118px;}
      .flow strong {display: block; color: #0b5137; font-size: 1.05rem; margin: .35rem 0;}
    </style>
    """,
    unsafe_allow_html=True,
)

qr_path = Path(__file__).resolve().parents[1] / "img" / "qr_code.jpeg"
qr_base64 = base64.b64encode(qr_path.read_bytes()).decode("ascii")

if True:
    st.markdown(
        f"""
        <div class="hero"><div class="hero-copy">
          <div class="eyebrow">Kosovo data app</div>
          <h1>🌾 Këshilltari i Fermerit</h1>
          <p>A simple evidence tool for a Kosovar farmer deciding when to consider selling a selected product. It turns public price, weather, cost-index, and inflation data into a transparent selling-timing view.</p>
          </div>
          <div class="hero-qr">
          <img src="data:image/jpeg;base64,{qr_base64}" alt="QR code for the app" />
          <span>Scan to open the app</span>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
# with hero_qr:
#     st.markdown("<div class='hero' style='padding: 1rem; text-align: center;'>", unsafe_allow_html=True)
#     st.image("img/qr_code.jpeg", caption="Scan to open the app", width=155)
#     st.markdown("</div>", unsafe_allow_html=True)

top_left, top_right = st.columns([1.3, 1])
with top_left:
    st.subheader("The question it answers")
    st.markdown(
        "> **“For this selected product, does the historical evidence suggest selling now, waiting, or watching?”**"
    )
    st.write(
        "The app compares the latest Kosovo-level ASK product-price value with its normal seasonal level and the next three months' historical baseline. "
        "It does not claim to choose the best crop to plant or calculate a farm's profit."
    )
with top_right:
    st.info("**Built for one decision**\n\nSelling timing—not crop selection, investment advice, or a guaranteed forecast.")
    if st.button("Open Këshilltari i Fermerit", icon="🌾", type="primary", use_container_width=True):
        st.session_state["advisor_opened"] = True
        st.switch_page("app.py")

st.subheader("How the evidence becomes a decision")
f1, arrow1, f2, arrow2, f3 = st.columns([1.35, .22, 1.35, .22, 1.35])
with f1:
    st.markdown("<div class='flow'>📊<strong>1. Select a product</strong>Monthly ASKdata price history for the selected product.</div>", unsafe_allow_html=True)
with arrow1:
    st.markdown("<div style='text-align:center;font-size:1.8rem;padding-top:2.4rem;color:#1d9e75'>→</div>", unsafe_allow_html=True)
with f2:
    st.markdown("<div class='flow'>🗓️<strong>2. Compare seasonal evidence</strong>Latest value, historical month pattern, range, and next-month baseline.</div>", unsafe_allow_html=True)
with arrow2:
    st.markdown("<div style='text-align:center;font-size:1.8rem;padding-top:2.4rem;color:#1d9e75'>→</div>", unsafe_allow_html=True)
with f3:
    st.markdown("<div class='flow'>💡<strong>3. Read a cautious signal</strong>Sell now, wait/watch, or watch—with the rule and uncertainty visible.</div>", unsafe_allow_html=True)

st.divider()
st.subheader("What data is used")
c1, c2, c3 = st.columns(3)
with c1:
    st.markdown("<div class='card'><h3>📈 ASKdata</h3><b>Product prices</b><br>Monthly Kosovo-level product-price series for the selling calendar and baseline.<br><br><b>Input/output indices</b><br>National agricultural price-cost context.</div>", unsafe_allow_html=True)
with c2:
    st.markdown("<div class='card'><h3>🌦️ Open-Meteo</h3>Monthly rainfall and temperature at the selected city coordinate, used as clearly labelled local context beside national prices.<br><br>It is not Kosovo-wide weather.</div>", unsafe_allow_html=True)
with c3:
    st.markdown("<div class='card'><h3>💶 World Bank</h3>Kosovo annual CPI inflation, used for an approximate 2022-money view of earlier product-price values.<br><br>Annual CPI is not a monthly index.</div>", unsafe_allow_html=True)

st.subheader("What the charts mean")
meaning_left, meaning_right = st.columns(2)
with meaning_left:
    st.markdown("""
    - **Selling calendar:** green line is the historical monthly average; the shaded area shows the middle half of observed values; the orange diamond is the latest value.
    - **Recent trend:** compares recent observations with the usual value for the current calendar month.
    - **Seasonal baseline:** a historical same-month average, not a trained forecast.
    """)
with meaning_right:
    st.markdown("""
    - **Weather context:** green line is a Kosovo-level ASK price; blue bars are rainfall at the selected city coordinate.
    - **Price-cost context:** compares national agricultural output and input indices rebased to Jan 2022 = 100.
    - **Real prices:** annual CPI approximation; later months are blank until CPI is published.
    """)

st.warning(
    "**Read this responsibly.** Historical patterns do not guarantee future prices. The app does not know a farmer's yield, storage costs, product quality, contracts, transport costs, or local buyers. "
    "Weather association does not prove weather caused a price movement, and the price-cost ratio is not an individual farm's profit margin."
)

with st.expander("Data transparency and reliability"):
    st.markdown(
        """
        - Data is requested from live public APIs first and labelled **LIVE** when retrieved in the session.
        - If a source is unavailable, the app uses bundled **FALLBACK** snapshots so the demonstration remains usable.
        - The sidebar shows dataset coverage; normal app use does not overwrite snapshots.
        - Run `python scripts/validate_sources.py` for current endpoints, selected ASK codes, coverage, duplicates, null checks, and join coverage.
        - Full source and methodology notes are in `docs/data_sources.md`.
        """
    )

st.caption("Built for the Kosovo Data Science Hackathon. Sources: ASKdata / Kosovo Agency of Statistics, Open-Meteo Archive, and World Bank XKX.")
