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
    Supports city enrichment with coordinates and weather information.

    Used throughout the API to manage application state.
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

        if "city_name" not in temp_df.columns:
            raise ValueError("Missing 'city_name' column in CSV.")

        temp_df = temp_df[["city_name"]].copy()
        temp_df["city_name"] = temp_df["city_name"].astype(str).str.lower()

        temp_df = temp_df.drop_duplicates(subset="city_name").reset_index(drop=True)

        self.df = temp_df

    def save_cities_to_csv(self, file_path: str = "data/cities.csv") -> None:
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

        self.df = self.df[self.df["city_name"] != city_name_lower].reset_index(
            drop=True
        )

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
            raise ValueError(
                "DataFrame is uninitialized or empty. Nothing to export as JSON."
            )

        return self.df.to_dict(orient="records")

    def update_df_with_enrichment(self, enriched_data: list[dict]) -> bool:
        """
        Replaces the DataFrame with enriched data (after enrich_all_cities).
        Filters out rows with errors.

        Returns:
            bool: True if any enrichment failed (i.e., at least one row had an 'error' field), False otherwise.
        """
        df = pd.DataFrame(enriched_data)

        had_errors = "error" in df.columns and df["error"].notnull().any()

        if "error" in df.columns:
            df = df[df["error"].isnull()].drop(columns=["error"])

        self.df = df.reset_index(drop=True)
        return had_errors

    def update_enriched_city_data(self, enriched_data: dict) -> None:
        """
        Updates an existing city in the DataFrame with enriched data
        (coordinates and weather).

        Args:
            enriched_data (dict): Dictionary containing at least 'city_name',
                                and optionally: 'latitude', 'longitude', 'weather', 'temperature'.

        Raises:
            ValueError: If DataFrame is uninitialized or city is not found.
        """
        if self.df is None:
            raise ValueError("DataFrame is not initialized.")

        if "city_name" not in enriched_data:
            raise ValueError("Missing 'city_name' in enriched data.")

        city_name = enriched_data["city_name"].lower()

        if city_name not in self.df["city_name"].values:
            raise ValueError(f"City '{city_name}' not found in the DataFrame.")

        index = self.df.index[self.df["city_name"] == city_name].tolist()[0]

        for key in ["latitude", "longitude", "weather", "temperature"]:
            if key in enriched_data:
                self.df.at[index, key] = enriched_data[key]

    def get_cities_names(self) -> list[str]:
        """
        Returns a list of all city names currently in the DataFrame.

        Returns:
            list[str]: A list of city names as lowercase strings.

        Raises:
            ValueError: If the DataFrame is uninitialized or empty.
        """
        if self.df is None or self.df.empty:
            raise ValueError("DataFrame is uninitialized or empty.")

        return self.df["city_name"].tolist()

    async def find_closest_city(
        self, lat: float, lon: float, weather_service: WeatherService | None = None
    ) -> dict:
        """
        Finds the closest city in the DataFrame to the given coordinates,
        and returns its weather forecast and temperature.

        If weather data is missing for the closest city, attempts to fetch it on-demand.

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
            ValueError: If the DataFrame is uninitialized or missing coordinates.
        """
        if self.df is None or self.df.empty:
            raise ValueError("DataFrame is empty or uninitialized.")

        if "latitude" not in self.df.columns or "longitude" not in self.df.columns:
            raise ValueError(
                "Missing coordinates: Enrich cities before calling this endpoint."
            )

        distances = []
        for _, row in self.df.iterrows():
            city_lat = row["latitude"]
            city_lon = row["longitude"]

            if pd.isna(city_lat) or pd.isna(city_lon):
                distances.append(float("inf"))
            else:
                dist = haversine_distance(lat, lon, city_lat, city_lon)
                distances.append(dist)

        closest_idx = int(pd.Series(distances).idxmin())
        closest_row = self.df.loc[closest_idx]

        # Try to get existing weather data
        weather = closest_row.get("weather")
        temperature = closest_row.get("temperature")

        # If missing and service provided — fetch on demand
        if (pd.isna(weather) or pd.isna(temperature)) and weather_service is not None:
            result = await weather_service.fetch_weather(
                closest_row["latitude"], closest_row["longitude"]
            )
            if result:
                weather, temperature = result
                # Optional: update in df
                self.df.at[closest_idx, "weather"] = weather
                self.df.at[closest_idx, "temperature"] = temperature

        return {
            "city_name": closest_row["city_name"],
            "distance_km": round(distances[closest_idx], 2),
            "weather": weather,
            "temperature": temperature,
        }
