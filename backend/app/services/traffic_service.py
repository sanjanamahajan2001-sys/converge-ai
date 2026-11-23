"""Live traffic routing and delay calculation service using Google Maps Routes API."""

import logging
import os
import re
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

# Cache structure: key -> (timestamp, result_dict)
_TRAFFIC_CACHE: Dict[str, Tuple[datetime, Dict[str, Any]]] = {}
CACHE_TTL_SECONDS = 300  # 5 minutes cache to avoid redundant API quota usage


class TrafficService:
    """Service for querying real-time traffic conditions around the conference venue."""

    ROUTES_API_URL = "https://routes.googleapis.com/directions/v2:computeRoutes"

    @classmethod
    def get_api_key(cls) -> Optional[str]:
        """Resolve Google Maps server API key from settings or environment."""
        return settings.GOOGLE_MAPS_SERVER_API_KEY or os.getenv("GOOGLE_MAPS_SERVER_API_KEY")

    @classmethod
    def _parse_duration_seconds(cls, duration_str: str) -> int:
        """Parse Google duration string (e.g., '1235s') into integer seconds."""
        if not duration_str:
            return 0
        match = re.search(r"(\d+)", duration_str)
        return int(match.group(1)) if match else 0

    @classmethod
    async def get_traffic_summary(
        cls,
        origin: str = "Mumbai Airport, Mumbai",
        destination: str = "Bandra Kurla Complex, Mumbai",
    ) -> Dict[str, Any]:
        """Calculate traffic conditions and return structured delay analysis."""
        cache_key = f"{origin}-->{destination}"
        now = datetime.now(timezone.utc)

        # Check cache
        if cache_key in _TRAFFIC_CACHE:
            cached_time, cached_data = _TRAFFIC_CACHE[cache_key]
            if (now - cached_time).total_seconds() < CACHE_TTL_SECONDS:
                return cached_data

        api_key = cls.get_api_key()
        if not api_key:
            logger.warning("GOOGLE_MAPS_SERVER_API_KEY not configured; returning mock traffic state.")
            return {
                "origin": origin,
                "destination": destination,
                "distance_km": 6.4,
                "duration_mins": 15,
                "delay_mins": 0,
                "congestion_level": "NORMAL",
                "summary": "Traffic flow near venue is normal. Average travel time ~15 mins.",
                "is_live": False,
            }

        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": api_key,
            "X-Goog-FieldMask": "routes.duration,routes.distanceMeters,routes.staticDuration",
        }
        payload = {
            "origin": {"address": origin},
            "destination": {"address": destination},
            "travelMode": "DRIVE",
            "routingPreference": "TRAFFIC_AWARE",
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(cls.ROUTES_API_URL, headers=headers, json=payload)

            if resp.status_code != 200:
                logger.error(f"Google Routes API error {resp.status_code}: {resp.text}")
                return {
                    "origin": origin,
                    "destination": destination,
                    "congestion_level": "UNKNOWN",
                    "summary": "Live traffic data temporarily unavailable.",
                    "is_live": False,
                }

            data = resp.json()
            routes = data.get("routes", [])
            if not routes:
                return {
                    "origin": origin,
                    "destination": destination,
                    "congestion_level": "NORMAL",
                    "summary": "No route delays detected.",
                    "is_live": True,
                }

            route = routes[0]
            distance_meters = route.get("distanceMeters", 0)
            duration_secs = cls._parse_duration_seconds(route.get("duration", "0s"))
            static_secs = cls._parse_duration_seconds(route.get("staticDuration", "0s"))

            delay_secs = max(0, duration_secs - static_secs)
            delay_mins = round(delay_secs / 60)
            duration_mins = round(duration_secs / 60)
            distance_km = round(distance_meters / 1000, 1)

            if delay_mins >= 8:
                congestion = "HEAVY"
                summary = (
                    f"⚠️ Heavy traffic reported on routes towards venue (+{delay_mins}m delay). "
                    f"Current drive time: ~{duration_mins} mins ({distance_km} km)."
                )
            elif delay_mins >= 3:
                congestion = "MODERATE"
                summary = (
                    f"🚗 Moderate traffic slowdown (+{delay_mins}m delay) towards venue. "
                    f"Current drive time: ~{duration_mins} mins."
                )
            else:
                congestion = "NORMAL"
                summary = (
                    f"🟢 Traffic moving smoothly towards venue. Drive time is ~{duration_mins} mins ({distance_km} km)."
                )

            result = {
                "origin": origin,
                "destination": destination,
                "distance_km": distance_km,
                "duration_mins": duration_mins,
                "delay_mins": delay_mins,
                "congestion_level": congestion,
                "summary": summary,
                "is_live": True,
            }

            _TRAFFIC_CACHE[cache_key] = (now, result)
            return result

        except Exception as exc:
            logger.exception(f"Unexpected error querying Google Routes API: {exc}")
            return {
                "origin": origin,
                "destination": destination,
                "congestion_level": "UNKNOWN",
                "summary": "Traffic lookup failed.",
                "is_live": False,
            }
