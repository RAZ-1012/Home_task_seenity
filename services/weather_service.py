import httpx
import os
from dotenv import load_dotenv
import asyncio
from typing import Optional
import math
from httpx import HTTPStatusError
from asyncio import Semaphore

load_dotenv()

open_weather_key = os.getenv("OPENWEATHER_API_KEY")
WEATHER_URL = "https://api.openweathermap.org/data/2.5/weather"


class WeatherService:
    """
    A service to fetch current weather data (description and temperature)
    based on geographic coordinates using the OpenWeatherMap API.
    """

    _instance = None  # class-level singleton reference

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(WeatherService, cls).__new__(cls)
        return cls._instance

    def __init__(self, api_key: str = open_weather_key, max_concurrent_requests: int = 10):
        # Prevent re-initialization
        if hasattr(self, "_initialized") and self._initialized:
            return

        if not api_key:
            raise ValueError("Missing OpenWeatherMap API key.")

        self.api_key = api_key
        self.semaphore = Semaphore(max_concurrent_requests)
        self._initialized = True

    async def fetch_weather(self, lat: float, lon: float) -> Optional[tuple[str, float]]:
        """
        Fetches the current weather description and temperature for given coordinates.

        Args:
            lat (float): Latitude.
            lon (float): Longitude.

        Returns:
            Optional[tuple[str, float]]: (description, temperature) or None if not found.
        """
        params = {
            "lat": lat,
            "lon": lon,
            "appid": self.api_key,
            "units": "metric"
        }

        async with self.semaphore:
            async with httpx.AsyncClient(timeout=10.0) as client:
                try:
                    response = await client.get(WEATHER_URL, params=params)
                    response.raise_for_status()
                except httpx.RequestError as e:
                    print(f"[NETWORK ERROR] Weather request failed for ({lat}, {lon}): {e}")
                    return None
                except HTTPStatusError as e:
                    print(f"[HTTP ERROR] Weather fetch error for ({lat}, {lon}): {e.response.status_code}")
                    return None

        data = response.json()
        if "weather" not in data or not data["weather"]:
            return None

        description = data["weather"][0]["description"]
        temperature = data["main"]["temp"]
        return (description, temperature)

    async def fetch_multiple_weather(self, locations: list[tuple[float, float]]) -> list[Optional[tuple[str, float]]]:
        """
        Fetches weather for a list of coordinates concurrently.
        Skips invalid coordinates (None or NaN).

        Args:
            locations (list[tuple[float, float]]): List of (lat, lon) tuples.

        Returns:
            list[Optional[tuple[str, float]]]: List of (description, temperature).
        """

        tasks = []
        for lat, lon in locations:
            if (
                lat is None or lon is None or
                isinstance(lat, float) and math.isnan(lat) or
                isinstance(lon, float) and math.isnan(lon)
            ):
                tasks.append(asyncio.sleep(0, result=None))  # Skip with dummy result
            else:
                tasks.append(self.fetch_weather(lat, lon))

        return await asyncio.gather(*tasks, return_exceptions=False)