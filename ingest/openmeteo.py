"""Monthly weather for Kosovo regions from the Open-Meteo historical archive (no key)."""
import pandas as pd
import requests

from .common import retry_get

REGIONS = {
    "Prishtina": (42.6629, 21.1655),
    "Prizren":   (42.2139, 20.7397),
    "Peja":      (42.6609, 20.2888),
    "Gjakova":   (42.3803, 20.4308),
    "Mitrovica": (42.8914, 20.8660),
    "Ferizaj":   (42.3702, 21.1553),
    "Gjilan":    (42.4635, 21.4694),
}
ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"

def fetch_monthly_weather(region: str = "Prishtina", start: str = "2022-01-01") -> pd.DataFrame:
    """Daily rain/temperature aggregated to calendar months. Columns: date, rain_mm, temp_c."""
    lat, lon = REGIONS[region]
    end = (pd.Timestamp.today() - pd.Timedelta(days=7)).strftime("%Y-%m-%d")
    r = retry_get(ARCHIVE_URL, params={
        "latitude": lat, "longitude": lon,
        "start_date": start, "end_date": end,
        "daily": "precipitation_sum,temperature_2m_mean",
        "timezone": "auto",
    })
    r.raise_for_status()
    d = r.json()["daily"]
    df = pd.DataFrame({"day": pd.to_datetime(d["time"]),
                       "rain": d["precipitation_sum"],
                       "temp": d["temperature_2m_mean"]})
    m = df.set_index("day").resample("MS").agg(rain_mm=("rain", "sum"), temp_c=("temp", "mean"))
    return m.reset_index().rename(columns={"day": "date"})
