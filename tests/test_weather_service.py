import pytest
import httpx
from services.weather_service import WeatherService


@pytest.mark.asyncio
async def test_fetch_weather_success(monkeypatch):
    # Mock response for httpx
    async def mock_get(*args, **kwargs):
        class MockResponse:
            status_code = 200

            def raise_for_status(self):
                pass  # simulate OK

            def json(self):
                return {
                    "weather": [{"description": "clear sky"}],
                    "main": {"temp": 27.5},
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
