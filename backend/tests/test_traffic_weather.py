"""Unit test suite for TrafficService (Google Routes API) and WeatherService (Open-Meteo)."""

import pytest
from unittest.mock import AsyncMock, patch

from app.services.traffic_service import TrafficService
from app.services.weather_service import WeatherService


@pytest.mark.asyncio
async def test_weather_service_live_or_fallback():
    """Verify WeatherService returns valid structured weather summary."""
    weather = await WeatherService.get_weather_summary(latitude=19.0657, longitude=72.8687, city="Mumbai")
    assert "temperature_c" in weather
    assert "condition" in weather
    assert "summary" in weather
    assert weather["city"] == "Mumbai"
    assert isinstance(weather["temperature_c"], (int, float))


@pytest.mark.asyncio
async def test_traffic_service_parsing():
    """Verify TrafficService duration parsing helper."""
    assert TrafficService._parse_duration_seconds("1235s") == 1235
    assert TrafficService._parse_duration_seconds("45s") == 45
    assert TrafficService._parse_duration_seconds("") == 0


@pytest.mark.asyncio
async def test_traffic_service_live_or_mock():
    """Verify TrafficService returns delay analysis and congestion level."""
    traffic = await TrafficService.get_traffic_summary()
    assert "congestion_level" in traffic
    assert "summary" in traffic
    assert traffic["congestion_level"] in {"NORMAL", "MODERATE", "HEAVY", "UNKNOWN"}
    if traffic.get("is_live"):
        assert "duration_mins" in traffic
        assert "delay_mins" in traffic
