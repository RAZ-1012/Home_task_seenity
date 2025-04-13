import math
import pandas as pd

def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculates the great-circle distance in kilometers between two points
    on the Earth specified by their latitude and longitude using the Haversine formula.

    Args:
        lat1 (float): Latitude of the first point.
        lon1 (float): Longitude of the first point.
        lat2 (float): Latitude of the second point.
        lon2 (float): Longitude of the second point.

    Returns:
        float: Distance in kilometers.
    """
    R = 6371  # Earth radius in kilometers

    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)

    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return R * c

def is_valid_coordinates(lat: float, lon: float) -> bool:
    """
    Validates whether the given latitude and longitude values are within valid Earth ranges
    and are numeric types.

    Args:
        lat (float): Latitude to check.
        lon (float): Longitude to check.

    Returns:
        bool: True if valid, False otherwise.
    """
    if not isinstance(lat, (int, float)) or not isinstance(lon, (int, float)):
        return False
    return -90 <= lat <= 90 and -180 <= lon <= 180

def analyze_enrichment_status(df: pd.DataFrame) -> dict:
    """
    Analyzes the enrichment status of a DataFrame containing
    'lat', 'lon', 'weather', and 'temperature' columns.

    Args:
        df (pd.DataFrame): The DataFrame to analyze.

    Returns:
        dict: {
            "enriched_count": int,
            "failed_count": int,
            "failed_cities": list[str]
        }
    """
    total_rows = len(df)

    required_cols = ["lat", "lon", "weather", "temperature"]
    success_mask = df[required_cols].notna().all(axis=1)
    
    enriched_count = success_mask.sum()
    failed_cities = df.loc[~success_mask, "city_name"].tolist()
    failed_count = total_rows - enriched_count

    return {
        "enriched_count": enriched_count,
        "failed_count": failed_count,
        "failed_cities": failed_cities
    }