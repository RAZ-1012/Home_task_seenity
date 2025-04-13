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
    file_storage = FileStorage(stream=BytesIO(csv_data), filename="cities.csv", content_type="text/csv")
    
    manager = DataManager()
    manager.load_cities_from_csv_file(file_storage)

    assert "city_name" in manager.df.columns
    assert len(manager.df) == 2
    assert manager.df.iloc[0]["city_name"] == "tel aviv"
