"""Lags must be true calendar lags, even across a seasonal crop's off-season gap."""
import pandas as pd

import analysis


def test_weather_lags_are_true_calendar_lags():
    prices = pd.DataFrame(
        [("Tomatoes", "2024-06-01", 2.0)], columns=["product", "date", "price"]
    ).assign(date=lambda x: pd.to_datetime(x["date"]))
    weather = pd.DataFrame({
        "date": pd.to_datetime(["2023-09-01", "2024-04-01", "2024-05-01", "2024-06-01"]),
        "rain_mm": [99.0, 10.0, 20.0, 30.0],
        "temp_c": [1.0, 2.0, 3.0, 4.0],
    })
    panel = analysis.weather_price_panel(prices, weather, "Tomatoes")
    assert panel.iloc[0]["rain_lag1"] == 20.0  # May 2024 - NOT September 2023
    assert panel.iloc[0]["rain_lag2"] == 10.0  # April 2024
