import pytest
import httpx
from services.weather_service import WeatherService

@pytest.mark.asyncio
async def test_fetch_weather_success(monkeypatch):
    # Mock response for httpx
    async def mock_get(*args, **kwargs):
        class MockResponse:
            status_code = 200
            def raise_for_status(self): pass  # simulate OK
            def json(self):
                return {
                    "weather": [{"description": "clear sky"}],
                    "main": {"temp": 27.5}
                }
        return MockResponse()

    monkeypatch.setattr("httpx.AsyncClient.get", mock_get)

    service = WeatherService()
    result = await service.fetch_weather(32.08, 34.78)

    assert result == ("clear sky", 27.5)


@pytest.mark.asyncio
async def test_fetch_weather_failure(monkeypatch):
    async def mock_get(*args, **kwargs):
        class MockResponse:
            status_code = 404
            def raise_for_status(self):
                raise httpx.HTTPStatusError("Not Found", request=None, response=self)
            def json(self):
                return {}
        return MockResponse()

    monkeypatch.setattr("httpx.AsyncClient.get", mock_get)

    service = WeatherService()
    result = await service.fetch_weather(0, 0)
    assert result is None


@pytest.mark.asyncio
async def test_fetch_multiple_weather(monkeypatch):
    async def mock_fetch_weather(self, lat, lon):
        return (f"desc-{lat}", 20.0 + lat)

    monkeypatch.setattr(WeatherService, "fetch_weather", mock_fetch_weather)

    service = WeatherService()
    results = await service.fetch_multiple_weather([(32.0, 34.0), (None, 34.0), (31.0, 35.0)])

    assert results[0] == ("desc-32.0", 52.0)
    assert results[1] is None
    assert results[2] == ("desc-31.0", 51.0)