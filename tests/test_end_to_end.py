import io
import pytest
from app import create_app

@pytest.fixture
def client():
    app = create_app()
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


def test_enrich_and_error_handling_flow(client):
    # Upload CSV with duplicates and invalid city
    city_data = b"""city_name
paris
new york
tel aviv
paris
new york
tal avivi
"""

    data = {
        "file": (io.BytesIO(city_data), "cities.csv")
    }

    res = client.post("/upload-cities", content_type='multipart/form-data', data=data)
    assert res.status_code == 200
    assert b"cities loaded successfully" in res.data

    # Enrich data
    res = client.post("/enrich-data")
    assert res.status_code in (200, 207)
    json_data = res.get_json()

    assert "enriched_count" in json_data
    assert "failed_count" in json_data
    assert "failed_cities" in json_data

    # expect at least one city to fail (tal avivi)
    assert "tal avivi" in [c.lower() for c in json_data["failed_cities"]]

    # Get all cities and ensure duplicates are not inserted twice
    res = client.get("/get-all-cities")
    assert res.status_code == 200
    cities = res.get_json()["cities"]
    city_names = [c["city_name"].lower() for c in cities]

    # Check duplicates are handled (paris should appear once)
    assert city_names.count("paris") == 1
    assert "tal avivi" in city_names  

    # Try closest-city with valid input
    res = client.post("/closest-city", json={"lat": 32.08, "lon": 34.78})
    assert res.status_code == 200
    assert "city_name" in res.get_json()

    # Try closest-city with missing lon
    res = client.post("/closest-city", json={"lat": 32.08})
    assert res.status_code == 400
    assert "error" in res.get_json()

    # Try closest-city with invalid type
    res = client.post("/closest-city", json={"lat": "hello", "lon": 34.78})
    assert res.status_code == 400
    assert "error" in res.get_json()

    # Delete non-existing city
    res = client.delete("/delete-city/doesnotexist")
    assert res.status_code == 404

    # Delete an existing city and recheck
    res = client.delete("/delete-city/paris")
    assert res.status_code == 200
    res = client.get("/get-all-cities")
    assert "paris" not in [c["city_name"].lower() for c in res.get_json()["cities"]]

    # Save and export
    res = client.post("/save-cities")
    assert res.status_code == 200

    res = client.get("/export-cities")
    assert res.status_code == 200
    assert res.mimetype == 'text/csv'