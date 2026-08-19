import pandas as pd

import analysis


def price_frame(rows):
    return pd.DataFrame(rows, columns=["product", "date", "price"]).assign(date=lambda x: pd.to_datetime(x["date"]))


def test_deflate_does_not_invent_future_cpi():
    prices = price_frame([("Potato", "2025-01-01", 10.0), ("Potato", "2026-01-01", 11.0)])
    inflation = pd.DataFrame({"year": [2022, 2023, 2024, 2025], "inflation_pct": [10.0, 5.0, 2.0, 3.0]})
    result = analysis.deflate(prices, inflation, "Potato")
    assert result.loc[result["date"] == pd.Timestamp("2025-01-01"), "real_price"].notna().all()
    assert result.loc[result["date"] == pd.Timestamp("2026-01-01"), "real_price"].isna().all()
    assert not result.loc[result["date"] == pd.Timestamp("2026-01-01"), "cpi_available"].any()


def test_forecast_requires_minimum_same_month_history():
    prices = price_frame([
        ("Potato", "2024-01-01", 1.0), ("Potato", "2025-01-01", 1.1), ("Potato", "2026-01-01", 1.2),
        ("Potato", "2024-02-01", 1.0),
        ("Potato", "2026-12-01", 1.0),
    ])
    result = analysis.forecast(prices, "Potato", horizon=2, min_observations=3)
    assert result["enough_history"].tolist() == [True, False]
    assert pd.isna(result.iloc[1]["forecast"])


def test_weather_panel_deduplicates_before_join():
    prices = price_frame([("Potato", "2024-01-01", 1.0), ("Potato", "2024-01-01", 1.1)])
    weather = pd.DataFrame({"date": pd.to_datetime(["2024-01-01", "2024-01-01"]), "rain_mm": [1, 2], "temp_c": [3, 4]})
    panel = analysis.weather_price_panel(prices, weather, "Potato")
    assert len(panel) == 1


def test_backtest_reports_no_value_without_history():
    prices = price_frame([("Potato", "2026-01-01", 1.0), ("Potato", "2026-02-01", 2.0)])
    assert analysis.forecast_backtest(prices, "Potato") == {"n": 0, "mae": None}
