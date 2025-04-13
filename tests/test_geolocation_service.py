import pytest
import httpx
from services.geolocation_service import GeolocationService


@pytest.mark.asyncio
async def test_fetch_coordinates_success(monkeypatch):
    # Mock successful response
    async def mock_get(*args, **kwargs):
        class MockResponse:
            status_code = 200
            def raise_for_status(self): pass
            def json(self):
                return {
                    "results": [
                        {"geometry": {"lat": 32.0853, "lng": 34.7818}}
                    ]
                }
        return MockResponse()

    monkeypatch.setattr("httpx.AsyncClient.get", mock_get)

    service = GeolocationService()
    result = await service.fetch_coordinates("Tel Aviv")

    assert result == (32.0853, 34.7818)


@pytest.mark.asyncio
async def test_fetch_coordinates_not_found(monkeypatch):
    # Mock response with empty results
    async def mock_get(*args, **kwargs):
        class MockResponse:
            status_code = 200
            def raise_for_status(self): pass
            def json(self):
                return {"results": []}
        return MockResponse()

    monkeypatch.setattr("httpx.AsyncClient.get", mock_get)

    service = GeolocationService()
    result = await service.fetch_coordinates("NotARealCity")

    assert result is None


@pytest.mark.asyncio
async def test_fetch_coordinates_api_error(monkeypatch):
    # Mock response that raises HTTPStatusError
    async def mock_get(*args, **kwargs):
        class MockResponse:
            status_code = 500
            def raise_for_status(self):
                raise httpx.HTTPStatusError("Internal Server Error", request=None, response=self)
            def json(self): return {}
        return MockResponse()

    monkeypatch.setattr("httpx.AsyncClient.get", mock_get)

    service = GeolocationService()
    result = await service.fetch_coordinates("Paris")

    assert result is None


@pytest.mark.asyncio
async def test_fetch_multiple_coordinates(monkeypatch):
    # Mock for fetch_coordinates inside the class
    async def mock_fetch_coordinates(self, city_name):
        if city_name == "Tel Aviv":
            return (32.0853, 34.7818)
        elif city_name == "Paris":
            return (48.8566, 2.3522)
        return None

    monkeypatch.setattr(GeolocationService, "fetch_coordinates", mock_fetch_coordinates)

    service = GeolocationService()
    result = await service.fetch_multiple_coordinates(["Tel Aviv", "Paris", "Fake City"])

    assert result["Tel Aviv"] == (32.0853, 34.7818)
    assert result["Paris"] == (48.8566, 2.3522)
    assert result["Fake City"] is None


@pytest.mark.asyncio
async def test_fetch_coordinates_prints_info_when_not_found(monkeypatch, capfd):
    # Mock empty result
    async def mock_get(*args, **kwargs):
        class MockResponse:
            status_code = 200
            def raise_for_status(self): pass
            def json(self):
                return {"results": []}
        return MockResponse()

    monkeypatch.setattr("httpx.AsyncClient.get", mock_get)

    service = GeolocationService()
    await service.fetch_coordinates("NotARealCity")

    out, _ = capfd.readouterr()
    assert "[INFO] No results found for city: NotARealCity" in out