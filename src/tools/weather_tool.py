import requests
import json
from langchain_core.tools import tool
from pydantic import BaseModel, Field

class WeatherInput(BaseModel):
    location_name: str = Field(description="City or district name (e.g., 'Meerut', 'Pune')")

@tool(args_schema=WeatherInput)
def fetch_weather_data(location_name: str) -> str:
    """Fetches real-time weather and 3-day forecasts for a given location."""
    try:
        geo_res = requests.get(
            f"https://geocoding-api.open-meteo.com/v1/search?name={location_name}&count=1&language=en&format=json",
            timeout=10
        ).json()

        if not geo_res.get("results"):
            return json.dumps({"error": f"Location '{location_name}' not found."})

        loc = geo_res["results"][0]
        lat, lon = loc["latitude"], loc["longitude"]

        params = {
            "latitude": lat,
            "longitude": lon,
            "current": ["temperature_2m", "relative_humidity_2m", "precipitation", "wind_speed_10m"],
            "daily": ["temperature_2m_max", "temperature_2m_min", "precipitation_probability_max"],
            "timezone": "auto",
            "forecast_days": 3
        }
        weather = requests.get("https://api.open-meteo.com/v1/forecast", params=params, timeout=10).json()

        return json.dumps({
            "location": f"{loc.get('name')}, {loc.get('country')}",
            "current": weather.get("current", {}),
            "forecast": weather.get("daily", {})
        })
    except Exception as e:
        return json.dumps({"error": str(e)})