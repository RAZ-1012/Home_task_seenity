import httpx
import os
from dotenv import load_dotenv
import asyncio
from typing import Optional
from httpx import HTTPStatusError
from asyncio import Semaphore

load_dotenv()

opencage_key = os.getenv("OPENCAGE_API_KEY")
GEOCODE_URL = "https://api.opencagedata.com/geocode/v1/json"


class GeolocationService:
    """
    A service that fetches geographical coordinates (latitude and longitude)
    for given city names using the OpenCage Geocoder API.
    """

    # _instance = None

    # def __new__(cls, *args, **kwargs):
    #     if cls._instance is None:
    #         cls._instance = super(GeolocationService, cls).__new__(cls)
    #     return cls._instance

    def __init__(self, api_key: str = opencage_key, max_concurrent_requests: int = 15):
        # Prevent re-initialization
        # if hasattr(self, "_initialized") and self._initialized:
        #     return

        if not api_key:
            raise ValueError("Missing OpenCage API key.")
        self.api_key = api_key
        self.semaphore = Semaphore(max_concurrent_requests)
        # self._initialized = True

    async def fetch_coordinates(self, city_name: str) -> Optional[tuple[float, float]]:
        """
        Sends an asynchronous API request to fetch coordinates for a single city.
        Uses semaphore to limit concurrent requests.

        Args:
            city_name (str): The name of the city.

        Returns:
            Optional[tuple[float, float]]: (latitude, longitude) or None if not found.
        """
        params = {
            "q": city_name,
            "key": self.api_key,
            "limit": 1,
            "no_annotations": 1
        }

        async with self.semaphore:
            async with httpx.AsyncClient(timeout=10.0) as client:
                try:
                    response = await client.get(GEOCODE_URL, params=params)
                    response.raise_for_status()
                except httpx.RequestError as e:
                    print(f"[NETWORK ERROR] While fetching {city_name}: {e}")
                    return None
                except HTTPStatusError as e:
                    print(f"[HTTP ERROR] Status error for {city_name}: {e.response.status_code}")
                    return None

        data = response.json()
        if not data['results']:
            print(f"[INFO] No results found for city: {city_name}")
            return None

        geometry = data['results'][0]['geometry']
        return (geometry['lat'], geometry['lng'])

    