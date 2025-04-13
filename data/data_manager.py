from __future__ import annotations

import pandas as pd
from io import BytesIO
from typing import Optional
from werkzeug.datastructures import FileStorage
from services.geolocation_service import GeolocationService
from services.weather_service import WeatherService
from core.utils import haversine_distance




class DataManager:
    """
    Manages city data loaded from a CSV file and stored in a pandas DataFrame.
    """

    def __init__(self) -> None:
        """
        Initializes the DataManager with an empty DataFrame.
        """
        self.df: Optional[pd.DataFrame] = None

    def load_cities_from_csv_file(self, file_storage: FileStorage) -> None:
        """
        Reads a CSV from a FileStorage object (e.g., from an API request)
        and updates the internal DataFrame with lowercase city names,
        removing duplicates.

        Args:
            file_storage (FileStorage): The uploaded file containing CSV data.

        Raises:
            ValueError: If the CSV is missing the 'city_name' column.
        """
        file_bytes: bytes = file_storage.read()
        file_stream = BytesIO(file_bytes)
        temp_df = pd.read_csv(file_stream)

        if 'city_name' not in temp_df.columns:
            raise ValueError("Missing 'city_name' column in CSV.")

        temp_df = temp_df[['city_name']].copy()
        temp_df['city_name'] = temp_df['city_name'].astype(str).str.lower()

        temp_df = temp_df.drop_duplicates(subset='city_name').reset_index(drop=True)

        self.df = temp_df

    def save_cities_to_csv(self, file_path: str="data/cities.csv") -> None:
        """
        Saves the current DataFrame to a CSV file.

        Args:
            file_path (str): The file path where the CSV will be saved.

        Raises:
            ValueError: If the DataFrame is None or empty.
        """
        if self.df is None or self.df.empty:
            raise ValueError("DataFrame is empty or uninitialized.")

        self.df.to_csv(file_path, index=False)

    def add_city(self, city_name: str) -> bool:
        """
        Adds a new city to the DataFrame if it doesn't already exist.
        Converts the city name to lowercase for consistency.

        Args:
            city_name (str): The name of the city to add.

        Returns:
            bool: True if the city was added, False if it already existed.

        Raises:
            ValueError: If the DataFrame is uninitialized.
        """
        if self.df is None:
            raise ValueError("DataFrame is not initialized. Load data first.")

        city_name_lower = city_name.lower()

        if city_name_lower in self.df["city_name"].values:
            return False 

        new_row = pd.DataFrame({"city_name": [city_name_lower]})
        self.df = pd.concat([self.df, new_row], ignore_index=True)
        return True
        
    def remove_city(self, city_name: str) -> None:
        """
        Removes any row(s) from the DataFrame that match the given city name (case-insensitive).
        The provided city_name is converted to lowercase before filtering.

        Args:
            city_name (str): The city name to remove.

        Raises:
            ValueError: If the DataFrame is uninitialized, or if no matching city was found in the DataFrame.
        """
        if self.df is None:
            raise ValueError("DataFrame is not initialized. Load data first.")

        city_name_lower = city_name.lower()
        initial_length = len(self.df)

        self.df = self.df[self.df['city_name'] != city_name_lower].reset_index(drop=True)

        # If no rows were removed, raise an error
        if len(self.df) == initial_length:
            raise ValueError(f"City '{city_name}' does not exist in the DataFrame.")
        
    def to_send(self) -> str:
        """
        Returns the entire DataFrame in JSON format with orient='records'.

        Raises:
            ValueError: If the DataFrame is uninitialized or empty.

        Returns:
            str: A JSON string representing the DataFrame rows.
        """
        if self.df is None or self.df.empty:
            raise ValueError("DataFrame is uninitialized or empty. Nothing to export as JSON.")

        return self.df.to_dict(orient='records')

    async def enrich_with_coordinates_from_api(self, geo_service: GeolocationService) -> None:
        """
        Enriches the internal DataFrame with latitude and longitude coordinates for each city,
        using the provided GeolocationService.

        This function sends asynchronous requests for all cities in the 'city_name' column
        and updates the DataFrame with 'lat' and 'lon' columns.

        Args:
            geo_service (GeolocationService): An instance of GeolocationService to fetch coordinates.

        Raises:
            ValueError: If the internal DataFrame is uninitialized or missing 'city_name' column.
        """
        if self.df is None or 'city_name' not in self.df.columns:
            raise ValueError("DataFrame is not initialized or missing 'city_name'.")

        cities = self.df['city_name'].tolist()
        city_to_coords = await geo_service.fetch_multiple_coordinates(cities)

        lat_list = []
        lon_list = []

        for city in cities:
            coords = city_to_coords.get(city)
            if coords is None:
                lat_list.append(None)
                lon_list.append(None)
            else:
                lat, lon = coords
                lat_list.append(lat)
                lon_list.append(lon)

        self.df['lat'] = lat_list
        self.df['lon'] = lon_list

    async def enrich_with_weather_from_api(self, weather_service: WeatherService) -> None:
        """
        Enriches the DataFrame with current weather information
        based on existing latitude and longitude columns.

        Adds two new columns:
        - 'weather' (description)
        - 'temperature' (in Celsius)

        Args:
            weather_service (WeatherService): Service to fetch weather data.

        Raises:
            ValueError: If DataFrame is uninitialized or missing coordinates.
        """
        if self.df is None or 'lat' not in self.df.columns or 'lon' not in self.df.columns:
            raise ValueError("DataFrame is not initialized or missing coordinates.")

        locations = list(zip(self.df['lat'], self.df['lon']))
        results = await weather_service.fetch_multiple_weather(locations)

        weather_descriptions = []
        temperatures = []

        for result in results:
            if result is None:
                weather_descriptions.append(None)
                temperatures.append(None)
            else:
                description, temp = result
                weather_descriptions.append(description)
                temperatures.append(temp)

        self.df['weather'] = weather_descriptions
        self.df['temperature'] = temperatures

    async def find_closest_city(self, lat: float, lon: float, weather_service: WeatherService | None = None) -> dict:
        """
        Finds the closest city in the DataFrame to the given coordinates,
        and returns its weather forecast and temperature.

        If coordinates are missing, runs coordinate enrichment.
        If weather data is missing, fetches it on-demand for the closest city only (if service is provided).

        Args:
            lat (float): Latitude of the point.
            lon (float): Longitude of the point.
            weather_service (WeatherService, optional): Used to fetch weather if not already available.

        Returns:
            dict: {
                "city_name": str,
                "distance_km": float,
                "weather": str,
                "temperature": float
            }

        Raises:
            ValueError: If the DataFrame is uninitialized.
        """
        if self.df is None:
            raise ValueError("DataFrame is empty or uninitialized.")

        if 'lat' not in self.df.columns or 'lon' not in self.df.columns:
            geo_service = GeolocationService()
            await self.enrich_with_coordinates_from_api(geo_service)

        distances = []
        for _, row in self.df.iterrows():
            city_lat = row['lat']
            city_lon = row['lon']

            if pd.isna(city_lat) or pd.isna(city_lon):
                distances.append(float('inf'))
            else:
                dist = haversine_distance(lat, lon, city_lat, city_lon)
                distances.append(dist)

        closest_idx = int(pd.Series(distances).idxmin())
        closest_row = self.df.loc[closest_idx]

        if weather_service is None:
            weather_service = WeatherService()
        weather = None
        temperature = None
        result = await weather_service.fetch_weather(closest_row["lat"], closest_row["lon"])
        if result:
            weather, temperature = result

        return {
            "city_name": closest_row["city_name"],
            "distance_km": round(distances[closest_idx], 2),
            "weather": weather,
            "temperature": temperature
        }

    async def enrich_city(city_name: str) -> bool:
        """
        Enriches a city with coordinates and weather data.
        If enrichment fails, returns False.

        Args:
            city_name (str): Name of the city to enrich.

        Returns:
            bool: True if enrichment was successful, False otherwise.
        """
        coords = await geo_service.fetch_coordinates(city_name)
        if coords is None:
            print(f"[ENRICH ERROR] Coordinates not found for '{city_name}'")
            return False

        lat, lon = coords
        weather = await weather_service.fetch_weather(lat, lon)
        if weather is None:
            print(f"[ENRICH ERROR] Weather not found for '{city_name}'")
            return False

        weather_description, temperature = weather
        data_manager.update_city_info(city_name, lat, lon, weather_description, temperature)
        return True