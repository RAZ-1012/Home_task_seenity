import pytest
import asyncio
from services.data_enrichment_service import enrich_single_city, enrich_all_cities


class MockGeoService:
    async def fetch_coordinates(self, city_name):
        if city_name == "fail_city":
            return None
        return (1.23, 4.56)


class MockWeatherService:
    async def fetch_weather(self, lat, lon):
        if lat == -1:
            return None
        return ("sunny", 25.5)


@pytest.mark.asyncio
async def test_enrich_single_city_success():
    result = await enrich_single_city("paris", MockGeoService(), MockWeatherService())
    assert result["city_name"] == "paris"
    assert result["latitude"] == 1.23
    assert result["weather"] == "sunny"


@pytest.mark.asyncio
async def test_enrich_single_city_coordinates_fail():
    result = await enrich_single_city(
        "fail_city", MockGeoService(), MockWeatherService()
    )
    assert result["city_name"] == "fail_city"
    assert "error" in result
    assert result["error"] == "Failed to get coordinates"


@pytest.mark.asyncio
async def test_enrich_single_city_weather_fail():
    class BadWeather(MockWeatherService):
        async def fetch_weather(self, lat, lon):
            return None

    result = await enrich_single_city("city", MockGeoService(), BadWeather())
    assert result["city_name"] == "city"
    assert "error" in result
    assert result["error"] == "Failed to get weather"


@pytest.mark.asyncio
async def test_enrich_all_cities_mixed_results(monkeypatch):
    # Mocks
    async def mock_fetch_coordinates(self, city_name):
        if city_name == "fail_city":
            return None
        return (1.23, 4.56)

    async def mock_fetch_weather(self, lat, lon):
        return ("sunny", 25.5)

    from services.geolocation_service import GeolocationService
    from services.weather_service import WeatherService

    monkeypatch.setattr(GeolocationService, "fetch_coordinates", mock_fetch_coordinates)
    monkeypatch.setattr(WeatherService, "fetch_weather", mock_fetch_weather)

    cities = ["paris", "fail_city"]
    results = await enrich_all_cities(cities)

    assert len(results) == 2
    assert any("error" in r for r in results)
    assert any(r["city_name"] == "fail_city" for r in results)
