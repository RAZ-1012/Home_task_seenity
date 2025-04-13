from typing import Optional, List
from services.geolocation_service import GeolocationService
from services.weather_service import WeatherService
import asyncio


async def enrich_single_city(
    city_name: str, geo_service: GeolocationService, weather_service: WeatherService
) -> dict:
    """
    Enrich a single city with coordinates and weather data.

    Args:
        city_name (str): The name of the city.
        geo_service (GeolocationService): Service for geolocation.
        weather_service (WeatherService): Service for weather data.

    Returns:
        dict: Enriched city data or error message.
    """
    coords: Optional[tuple[float, float]] = await geo_service.fetch_coordinates(
        city_name
    )
    if coords is None:
        return {"city_name": city_name, "error": "Failed to get coordinates"}

    lat, lon = coords
    weather: Optional[tuple[str, float]] = await weather_service.fetch_weather(lat, lon)
    if weather is None:
        return {
            "city_name": city_name,
            "latitude": lat,
            "longitude": lon,
            "error": "Failed to get weather",
        }

    weather_desc, temperature = weather

    return {
        "city_name": city_name,
        "latitude": lat,
        "longitude": lon,
        "weather": weather_desc,
        "temperature": temperature,
    }


async def enrich_all_cities(city_names: List[str]) -> List[dict]:
    """
    Enriches a list of cities concurrently with coordinates and weather data.

    Args:
        city_names (List[str]): List of city names.

    Returns:
        List[dict]: List of enriched city data.
    """
    geo_service = GeolocationService()
    weather_service = WeatherService()

    tasks = [
        enrich_single_city(city, geo_service, weather_service) for city in city_names
    ]
    results = await asyncio.gather(*tasks)
    return results
