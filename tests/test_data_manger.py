import pytest
import pandas as pd
from data.data_manager import DataManager
from werkzeug.datastructures import FileStorage
from io import BytesIO


# Test adding a city to an initialized DataFrame
def test_add_city_to_initialized_df():
    manager = DataManager()
    manager.df = pd.DataFrame(columns=["city_name"])

    manager.add_city("Tel Aviv")

    assert len(manager.df) == 1
    assert manager.df.iloc[0]["city_name"] == "tel aviv"


# Test adding a city when the DataFrame is not initialized should raise an error
def test_add_city_to_uninitialized_df_raises():
    manager = DataManager()

    with pytest.raises(ValueError):
        manager.add_city("Tel Aviv")


# Test removing a city that exists in the DataFrame
def test_remove_city_success():
    manager = DataManager()
    manager.df = pd.DataFrame({"city_name": ["tel aviv", "paris"]})

    manager.remove_city("Paris")

    assert len(manager.df) == 1
    assert manager.df.iloc[0]["city_name"] == "tel aviv"


# Test removing a city that does not exist should raise an error
def test_remove_city_not_found_raises():
    manager = DataManager()
    manager.df = pd.DataFrame({"city_name": ["tel aviv"]})

    with pytest.raises(ValueError):
        manager.remove_city("Paris")


# Test loading cities from a valid CSV FileStorage
def test_load_cities_from_csv_file_success():
    # Create an in-memory CSV file
    csv_data = b"city_name\ntel aviv\nlondon"
    file_storage = FileStorage(
        stream=BytesIO(csv_data), filename="cities.csv", content_type="text/csv"
    )

    manager = DataManager()
    manager.load_cities_from_csv_file(file_storage)

    assert "city_name" in manager.df.columns
    assert len(manager.df) == 2
    assert manager.df.iloc[0]["city_name"] == "tel aviv"


def test_get_cities_names_success():
    manager = DataManager()
    manager.df = pd.DataFrame({"city_name": ["tel aviv", "paris"]})

    names = manager.get_cities_names()

    assert isinstance(names, list)
    assert names == ["tel aviv", "paris"]


def test_get_cities_names_raises_on_empty_df():
    manager = DataManager()
    manager.df = pd.DataFrame(columns=["city_name"])

    with pytest.raises(ValueError):
        manager.get_cities_names()


def test_update_enriched_city_data_success():
    manager = DataManager()
    manager.df = pd.DataFrame({"city_name": ["tel aviv"]})

    enriched_data = {
        "city_name": "tel aviv",
        "latitude": 32.08,
        "longitude": 34.78,
        "weather": "clear sky",
        "temperature": 27.5,
    }

    manager.update_enriched_city_data(enriched_data)

    row = manager.df.iloc[0]
    assert row["latitude"] == 32.08
    assert row["longitude"] == 34.78
    assert row["weather"] == "clear sky"
    assert row["temperature"] == 27.5


def test_update_df_with_enrichment_filters_errors():
    manager = DataManager()

    enriched_data = [
        {
            "city_name": "paris",
            "latitude": 48.85,
            "longitude": 2.35,
            "weather": "cloudy",
            "temperature": 18.2,
        },
        {"city_name": "unknown", "error": "City not found"},
    ]

    had_errors = manager.update_df_with_enrichment(enriched_data)

    assert int(had_errors) == 1
    assert len(manager.df) == 1
    assert "error" not in manager.df.columns
    assert manager.df.iloc[0]["city_name"] == "paris"
