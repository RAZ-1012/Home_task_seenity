import os
import asyncio
from flask import request, jsonify, send_file
from werkzeug.datastructures import FileStorage
from dotenv import load_dotenv

from data.data_manager import DataManager
from services.weather_service import WeatherService
from services.geolocation_service import GeolocationService
from services.data_enrichment_service import enrich_all_cities, enrich_single_city
from core.utils import is_valid_coordinates

# Loading path to save
load_dotenv()
CITIES_CSV_PATH = os.getenv("CITIES_CSV_PATH", "data/cities.csv")

# Global service instances
data_manager = DataManager()
geo_service = GeolocationService()
weather_service = WeatherService()


def register_routes(app):
    """
    Registers all API endpoints to the given Flask app instance.
    """

    @app.route("/", methods=["GET"])
    def index():
        """
        Health check endpoint.

        Returns:
            200 OK: Confirmation that the API is running.
        """
        return jsonify({"message": "City Weather API is running"}), 200

    @app.route("/upload-cities", methods=["POST"])
    def upload_cities():
        """
        Uploads a CSV file containing city names.
        Expects multipart/form-data with a 'file' field.

        Returns:
            200 OK: Cities loaded successfully.
            400 Bad Request: Missing or invalid file.
            500 Internal Server Error: Failed to process file.
        """
        if "file" not in request.files:
            return jsonify({"error": "Missing file"}), 400

        file: FileStorage = request.files["file"]

        try:
            data_manager.load_cities_from_csv_file(file)
            count = len(data_manager.df)

            return (
                jsonify(
                    {"message": f"{count} cities loaded successfully.", "count": count}
                ),
                200,
            )

        except ValueError as ve:
            return jsonify({"error": str(ve)}), 400
        except Exception:
            return jsonify({"error": "Unexpected error during file upload."}), 500

    @app.route("/upload-and-enrich", methods=["POST"])
    async def upload_and_enrich():
        """
        Uploads a CSV file of cities and immediately enriches them with coordinates and weather data.

        Expects:
            multipart/form-data with a 'file' field containing a CSV with 'city_name' column.

        Returns:
            200 OK: All cities uploaded and enriched successfully.
            207 Multi-Status: Some cities enriched, some failed.
            400 Bad Request: Missing or invalid file.
            500 Internal Server Error: Unexpected failure during upload or enrichment.
        """
        if "file" not in request.files:
            return jsonify({"error": "Missing file"}), 400

        file: FileStorage = request.files["file"]

        try:
            # Load the cities from CSV
            data_manager.load_cities_from_csv_file(file)
            city_names = data_manager.get_cities_names()
            
            # Enrich the loaded cities
            enriched_results = await enrich_all_cities(city_names)
            had_failures = data_manager.update_df_with_enrichment(enriched_results)

            enriched_count = len(data_manager.df)
            failed_count = len(city_names) - enriched_count
            failed_cities = [
                item["city_name"]
                for item in enriched_results
                if "error" in item and item["error"] is not None
            ]

            response_body = {
                "message": "Upload and enrichment completed"
                + (" with some errors." if had_failures else " successfully."),
                "enriched_count": enriched_count,
                "failed_count": failed_count,
                "failed_cities": failed_cities,
            }

            return jsonify(response_body), 207 if had_failures else 200

        except ValueError as ve:
            return jsonify({"error": str(ve)}), 400
        except Exception as e:
            print(f"[ERROR] {e}")
            return (
                jsonify({"error": "Unexpected error during upload and enrichment"}),
                500,
            )

    @app.route("/enrich-data", methods=["POST"])
    async def enrich_all():
        """
        Enriches all loaded cities with coordinates and weather data using external APIs.
        The enrichment is performed asynchronously and concurrently for each city.

        Returns:
            200 OK: All cities were enriched successfully.
            207 Multi-Status: Some cities enriched, some failed.
            422 Unprocessable Entity: No cities loaded.
            500 Internal Server Error: Enrichment process failed unexpectedly.
        """
        if data_manager.df is None or data_manager.df.empty:
            return jsonify({"error": "No cities loaded"}), 422

        try:
            city_names = data_manager.get_cities_names()
            enriched_results = await enrich_all_cities(city_names)

            had_failures = data_manager.update_df_with_enrichment(enriched_results)

            enriched_count = len(data_manager.df)
            failed_count = len(city_names) - enriched_count
            failed_cities = [
                item["city_name"]
                for item in enriched_results
                if "error" in item and item["error"] is not None
            ]

            response_body = {
                "message": "Enrichment completed"
                + (" with some errors." if had_failures else " successfully."),
                "enriched_count": enriched_count,
                "failed_count": failed_count,
                "failed_cities": failed_cities,
            }

            return jsonify(response_body), 207 if had_failures else 200

        except Exception:
            return jsonify({"error": "Failed to enrich data"}), 500

    @app.route("/add-city", methods=["POST"])
    async def add_city():
        """
        Adds a new city to the list and enriches it with coordinates and weather data.

        Expects:
            JSON body: { "city_name": "City Name" }

        Returns:
            201 Created: City was added and enriched successfully.
            200 OK: City already exists in the list.
            400 Bad Request: Invalid or missing input.
            424 Failed Dependency: Enrichment failed; city not saved.
            500 Internal Server Error: Unexpected error occurred.
        """
        try:
            data = request.get_json()
            if not data or "city_name" not in data:
                return jsonify({"error": "Missing 'city_name' in request body"}), 400

            city_name = data["city_name"]
            added = data_manager.add_city(city_name)
            total = len(data_manager.df)

            if not added:
                return (
                    jsonify(
                        {
                            "message": f"City '{city_name}' already exists.",
                            "total_cities": total,
                            "new": False,
                        }
                    ),
                    200,
                )

            # Try to enrich the newly added city
            enriched = await enrich_single_city(city_name, geo_service, weather_service)

            if "error" in enriched:
                # Enrichment failed — remove the city we just added
                data_manager.remove_city(city_name)
                return (
                    jsonify(
                        {
                            "error": f"Failed to enrich city '{city_name}'. City was not saved.",
                            "details": enriched["error"],
                        }
                    ),
                    424,
                )  # Failed Dependency

            # Update existing city row with enrichment results
            data_manager.update_enriched_city_data(enriched)

            return (
                jsonify(
                    {
                        "message": f"City '{city_name}' added and enriched successfully.",
                        "total_cities": len(data_manager.df),
                        "new": True,
                    }
                ),
                201,
            )

        except ValueError as ve:
            return jsonify({"error": str(ve)}), 400
        except Exception as e:
            print(f"[ERROR] {e}")
            return jsonify({"error": "Failed to add city"}), 500

    @app.route("/closest-city", methods=["POST"])
    async def closest_city():
        """
        Finds the closest city in memory to the given coordinates.
        Automatically fetches weather if missing.

        Request Body:
            {
                "lat": float,
                "lon": float
            }

        Returns:
            200 OK: Closest city with distance and weather info.
            400 Bad Request: Missing or invalid input.
            422 Unprocessable Entity: No cities loaded.
            500 Internal Server Error: Failure during processing.
        """
        try:
            data = request.get_json()
            if not data or "lat" not in data or "lon" not in data:
                return jsonify({"error": "Missing 'lat' or 'lon' in request body"}), 400

            lat = data["lat"]
            lon = data["lon"]

            if not is_valid_coordinates(lat, lon):
                return jsonify({"error": "Invalid 'lon' or 'lat' value"}), 400

            if data_manager.df is None or data_manager.df.empty:
                return jsonify({"error": "No cities loaded"}), 422

            result = await data_manager.find_closest_city(
                lat=lat, lon=lon, weather_service=weather_service
            )

            return jsonify(result), 200

        except ValueError as ve:
            return jsonify({"error": str(ve)}), 400
        except Exception:
            return jsonify({"error": "Failed to find closest city"}), 500

    @app.route("/delete-city/<city_name>", methods=["DELETE"])
    def delete_city(city_name):
        """
        Deletes a city from the current DataFrame by name (case-insensitive).

        Args:
            city_name (str): The name of the city to delete (sent as path param).

        Returns:
            200 OK: City deleted successfully.
            404 Not Found: City not found.
            422 Unprocessable Entity: No data loaded.
            500 Internal Server Error: Deletion failed.
        """
        try:
            if data_manager.df is None or data_manager.df.empty:
                return jsonify({"error": "No cities loaded"}), 422

            data_manager.remove_city(city_name)
            total = len(data_manager.df)

            return (
                jsonify(
                    {
                        "message": f"City '{city_name}' removed successfully.",
                        "total_cities": total,
                    }
                ),
                200,
            )

        except ValueError as ve:
            return jsonify({"error": str(ve)}), 404
        except Exception:
            return jsonify({"error": "Failed to remove city"}), 500

    @app.route("/get-all-cities", methods=["GET"])
    def get_all_cities():
        """
        Returns the list of all cities as JSON.
        Each record includes city_name, coordinates and weather (if enriched).

        Returns:
            200 OK: Full list of cities.
            422 Unprocessable Entity: No data available.
            500 Internal Server Error: Retrieval failed.
        """
        try:
            data = data_manager.to_send()
            return jsonify({"cities": data, "count": len(data)}), 200
        except ValueError as ve:
            return jsonify({"error": str(ve)}), 422
        except Exception:
            return jsonify({"error": "Failed to retrieve city data"}), 500

    @app.route("/save-cities", methods=["POST"])
    def save_cities():
        """
        Saves the current list of cities to a local CSV file.

        Returns:
            200 OK: File saved successfully.
            422 Unprocessable Entity: No data to save.
            500 Internal Server Error: File save failed.
        """
        try:
            if data_manager.df is None or data_manager.df.empty:
                return jsonify({"error": "No data to save."}), 422

            data_manager.save_cities_to_csv(CITIES_CSV_PATH)

            return (
                jsonify(
                    {
                        "message": "City list saved successfully.",
                        "file_path": CITIES_CSV_PATH,
                    }
                ),
                200,
            )

        except Exception:
            return jsonify({"error": "Failed to save city data."}), 500

    @app.route("/export-cities", methods=["GET"])
    def export_cities():
        """
        Sends the saved CSV file as a download.
        If file doesn't exist, attempts to create it from memory.

        Returns:
            200 OK: CSV file as attachment.
            404 Not Found: No data available to export.
            500 Internal Server Error: Save or file read failed.
        """

        # If file does not exist, try to save it from memory if available
        if data_manager.df is None or data_manager.df.empty:
            return jsonify({"error": "No data available to export"}), 404

        try:
            data_manager.save_cities_to_csv(CITIES_CSV_PATH)
        except Exception:
            return jsonify({"error": "Failed to save cities before export"}), 500

        # Return the file as an attachment
        return send_file(
            CITIES_CSV_PATH,
            mimetype="text/csv",
            as_attachment=True,
            download_name="cities.csv",
        )
