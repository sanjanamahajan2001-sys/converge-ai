"""Live weather integration service using Open-Meteo for conference ambient context."""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple

import httpx

logger = logging.getLogger(__name__)

# In-memory weather cache: key -> (timestamp, weather_dict)
_WEATHER_CACHE: Dict[str, Tuple[datetime, Dict[str, Any]]] = {}
WEATHER_CACHE_TTL_SECONDS = 600  # 10 minutes cache


class WeatherService:
    """Service providing real-time weather conditions for conference venues."""

    OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"

    WMO_CODES = {
        0: "Clear sky",
        1: "Mainly clear",
        2: "Partly cloudy",
        3: "Overcast",
        45: "Foggy",
        48: "Depositing rime fog",
        51: "Light drizzle",
        53: "Moderate drizzle",
        55: "Dense drizzle",
        61: "Slight rain",
        63: "Moderate rain",
        65: "Heavy rain",
        80: "Slight rain showers",
        81: "Moderate rain showers",
        82: "Violent rain showers",
        95: "Thunderstorm",
    }

    @classmethod
    async def get_weather_summary(
        cls,
        latitude: float = 19.0657,
        longitude: float = 72.8687,
        city: str = "Mumbai",
    ) -> Dict[str, Any]:
        """Fetch current weather from Open-Meteo with caching."""
        cache_key = f"{round(latitude, 3)},{round(longitude, 3)}"
        now = datetime.now(timezone.utc)

        if cache_key in _WEATHER_CACHE:
            cached_time, cached_data = _WEATHER_CACHE[cache_key]
            if (now - cached_time).total_seconds() < WEATHER_CACHE_TTL_SECONDS:
                return cached_data

        params = {
            "latitude": latitude,
            "longitude": longitude,
            "current": "temperature_2m,relative_humidity_2m,precipitation,weather_code,wind_speed_10m",
        }

        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                resp = await client.get(cls.OPEN_METEO_URL, params=params)

            if resp.status_code != 200:
                logger.error(f"Open-Meteo returned status {resp.status_code}")
                return cls._fallback_weather(city)

            data = resp.json()
            current = data.get("current", {})

            temp_c = current.get("temperature_2m", 30.0)
            humidity = current.get("relative_humidity_2m", 45)
            precip = current.get("precipitation", 0.0)
            weather_code = current.get("weather_code", 0)
            wind_speed = current.get("wind_speed_10m", 3.0)

            condition = cls.WMO_CODES.get(weather_code, "Pleasant")
            is_rainy = precip > 0.1 or weather_code in {51, 53, 55, 61, 63, 65, 80, 81, 82, 95}

            if is_rainy:
                summary = f"🌧️ {city} Weather: {temp_c}°C with {condition.lower()}. Outdoor lawn networking is shifted to the indoor concourse."
            elif temp_c >= 33:
                summary = f"☀️ {city} Weather: Warm {temp_c}°C, {condition.lower()}. Central AC is running nicely inside conference halls."
            else:
                summary = f"🌤️ {city} Weather: Pleasant {temp_c}°C, {condition.lower()}. Great afternoon for patio and concourse discussions."

            result = {
                "city": city,
                "latitude": latitude,
                "longitude": longitude,
                "temperature_c": temp_c,
                "humidity_pct": humidity,
                "precipitation_mm": precip,
                "wind_speed_kmh": wind_speed,
                "condition": condition,
                "is_rainy": is_rainy,
                "summary": summary,
                "is_live": True,
            }

            _WEATHER_CACHE[cache_key] = (now, result)
            return result

        except Exception as exc:
            logger.exception(f"Failed to fetch live weather: {exc}")
            return cls._fallback_weather(city)

    @classmethod
    def _fallback_weather(cls, city: str) -> Dict[str, Any]:
        """Graceful fallback if network is unreachable."""
        return {
            "city": city,
            "temperature_c": 32.0,
            "humidity_pct": 40,
            "precipitation_mm": 0.0,
            "wind_speed_kmh": 4.0,
            "condition": "Clear",
            "is_rainy": False,
            "summary": f"☀️ {city} Weather: 32°C, pleasant clear sky inside the venue.",
            "is_live": False,
        }
