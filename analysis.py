"""Analysis layer: every function here produces a number that exists in NO single
source — the rubric's 'genuinely used together', plus all four named analysis
types: trends (seasonality), correlations (weather->price), comparisons
(output vs input costs), forecasts (seasonal average with a band)."""
import calendar

import pandas as pd

MONTH_NAMES = list(calendar.month_name)[1:]


# ---- trend: seasonality --------------------------------------------------

def seasonality(prices: pd.DataFrame, product: str) -> pd.DataFrame:
    """Average price per calendar month across all years. Columns: month, month_name, avg, std, n."""
    p = prices[prices["product"] == product].copy()
    p["month"] = p["date"].dt.month
    g = p.groupby("month")["price"].agg(avg="mean", std="std", n="count").reset_index()
    g["month_name"] = g["month"].map(lambda m: MONTH_NAMES[m - 1])
    return g.sort_values("month").reset_index(drop=True)


def best_month(season: pd.DataFrame) -> tuple[str, str]:
    """(best month to SELL = highest avg, cheapest month to BUY = lowest avg)."""
    hi = season.loc[season["avg"].idxmax(), "month_name"]
    lo = season.loc[season["avg"].idxmin(), "month_name"]
    return hi, lo


def seasonal_profile(prices: pd.DataFrame, product: str) -> pd.DataFrame:
    """Month-by-month distribution for an explainable seasonal price chart."""
    p = prices[prices["product"] == product].copy()
    p["month"] = p["date"].dt.month
    profile = p.groupby("month")["price"].agg(
        avg="mean", median="median", low="min", high="max", n="count",
        q25=lambda values: values.quantile(0.25),
        q75=lambda values: values.quantile(0.75),
    ).reset_index()
    profile["month_name"] = profile["month"].map(lambda month: MONTH_NAMES[month - 1])
    return profile.sort_values("month").reset_index(drop=True)


def selling_signal(latest: pd.Series, month_average: float, forecast: pd.DataFrame) -> dict:
    """A transparent, heuristic selling-timing label based only on displayed values."""
    upcoming = forecast.loc[forecast["enough_history"] & forecast["forecast"].notna(), "forecast"]
    next_average = float(upcoming.mean()) if not upcoming.empty else None
    current = float(latest["price"])
    versus_normal = current - month_average
    if next_average is None:
        return {"label": "WATCH", "reason": "Not enough history for the next-month seasonal baseline.", "next_average": None}
    if current >= month_average and next_average < current:
        return {"label": "SELL NOW", "reason": "Current value is at/above its usual month and the next seasonal baseline is lower.", "next_average": next_average}
    if current < month_average and next_average > current:
        return {"label": "WAIT / WATCH", "reason": "Current value is below its usual month and the next seasonal baseline is higher.", "next_average": next_average}
    return {"label": "WATCH", "reason": "Current and upcoming historical values give no strong timing advantage.", "next_average": next_average}


# ---- correlation: weather -> price ---------------------------------------

def weather_price_panel(prices: pd.DataFrame, weather: pd.DataFrame, product: str) -> pd.DataFrame:
    """Join ASKdata prices with Open-Meteo weather on month; add lagged weather.
    Lags are computed on the FULL monthly weather series BEFORE the join, so
    'rain_lag1' is always the true previous calendar month - even for seasonal
    crops whose price series has off-season gaps."""
    w = weather[["date", "rain_mm", "temp_c"]].drop_duplicates("date").sort_values("date").copy()
    for lag in (1, 2):
        w[f"rain_lag{lag}"] = w["rain_mm"].shift(lag)
        w[f"temp_lag{lag}"] = w["temp_c"].shift(lag)
    p = prices[prices["product"] == product][["date", "price"]].drop_duplicates("date")
    return p.merge(w, on="date", how="inner").sort_values("date").reset_index(drop=True)


def weather_correlations(panel: pd.DataFrame) -> dict:
    """Pearson r of price vs same-month and lagged rain/temperature."""
    out = {}
    for col in ("rain_mm", "rain_lag1", "rain_lag2", "temp_c", "temp_lag1", "temp_lag2"):
        s = panel[[col, "price"]].dropna()
        out[col] = round(float(s[col].corr(s["price"])), 2) if len(s) >= 12 else None
    return out


# ---- comparison: margin squeeze ------------------------------------------

def margin_squeeze(out_idx: pd.DataFrame, in_idx: pd.DataFrame,
                   anchor: str = "2022-01-01") -> pd.DataFrame:
    """Rebase both indices to anchor month = 100 (their official base years differ),
    then ratio >100 means prices outran costs; <100 means costs are winning.
    Columns: date, out_rebased, in_rebased, margin."""
    m = out_idx.merge(in_idx, on="date", how="inner").sort_values("date")
    a = m.loc[m["date"] == pd.Timestamp(anchor)]
    if a.empty:
        a = m.iloc[[0]]
    m["out_rebased"] = m["out_index"] / float(a["out_index"].iloc[0]) * 100
    m["in_rebased"] = m["in_index"] / float(a["in_index"].iloc[0]) * 100
    m["margin"] = m["out_rebased"] / m["in_rebased"] * 100
    return m.reset_index(drop=True)


# ---- real prices via Kosovo (XKX) inflation -------------------------------

def deflate(prices: pd.DataFrame, inflation: pd.DataFrame, product: str,
            base_year: int = 2022) -> pd.DataFrame:
    """Nominal -> real EUR (base-year money) using Kosovo's own CPI. Columns: date, price, real_price."""
    infl = inflation.drop_duplicates("year").set_index("year")["inflation_pct"]
    years = sorted(prices["date"].dt.year.unique())
    cpi, level = {}, 100.0
    for y in years:
        if y > base_year:
            if y not in infl.index:
                cpi[y] = None
                continue
            level *= 1 + float(infl.loc[y]) / 100
        cpi[y] = level
    cpi[base_year] = 100.0
    p = prices[prices["product"] == product][["date", "price"]].copy()
    p["real_price"] = p.apply(
        lambda r: r["price"] / cpi[r["date"].year] * 100
        if cpi.get(r["date"].year) is not None else float("nan"), axis=1
    )
    p["cpi_available"] = p["real_price"].notna()
    return p.reset_index(drop=True)


# ---- forecast: seasonal average with honest band --------------------------

def forecast(prices: pd.DataFrame, product: str, horizon: int = 3, min_observations: int = 3) -> pd.DataFrame:
    """Next months' expected price = average of the same calendar month in past
    years, band = +/-1 std. Deliberately simple and explainable to a judge.
    Columns: date, forecast, lo, hi."""
    season = seasonality(prices, product).set_index("month")
    last = prices[prices["product"] == product]["date"].max()
    rows = []
    for i in range(1, horizon + 1):
        d = (last + pd.DateOffset(months=i)).replace(day=1)
        if d.month not in season.index:
            rows.append({"date": d, "forecast": float("nan"), "lo": float("nan"), "hi": float("nan"),
                         "n": 0, "enough_history": False})
            continue
        s = season.loc[d.month]
        enough_history = int(s["n"]) >= min_observations
        std = 0.0 if pd.isna(s["std"]) else float(s["std"])
        rows.append({"date": d, "forecast": float(s["avg"]) if enough_history else float("nan"),
                     "lo": float(s["avg"]) - std if enough_history else float("nan"),
                     "hi": float(s["avg"]) + std if enough_history else float("nan"),
                     "n": int(s["n"]), "enough_history": enough_history})
    return pd.DataFrame(rows)


def forecast_backtest(prices: pd.DataFrame, product: str, min_observations: int = 3) -> dict:
    """Rolling-origin one-step seasonal-baseline accuracy, using past data only."""
    series = prices[prices["product"] == product][["date", "price"]].sort_values("date")
    errors = []
    for _, row in series.iterrows():
        history = series[series["date"] < row["date"]]
        same_month = history[history["date"].dt.month == row["date"].month]["price"]
        if len(same_month) >= min_observations:
            prediction = same_month.mean()
            errors.append(abs(row["price"] - prediction))
    if not errors:
        return {"n": 0, "mae": None}
    return {"n": len(errors), "mae": round(float(pd.Series(errors).mean()), 3)}
