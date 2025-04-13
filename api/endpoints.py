import os
from flask import request, jsonify, send_file
from werkzeug.datastructures import FileStorage
from data.data_manager import DataManager
from services.weather_service import WeatherService
from services.geolocation_service import GeolocationService
from core.utils import analyze_enrichment_status , is_valid_coordinates 

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

            return jsonify({
                "message": f"{count} cities loaded successfully.",
                "count": count
            }), 200

        except ValueError as ve:
            return jsonify({"error": str(ve)}), 400
        except Exception:
            return jsonify({"error": "Unexpected error during file upload."}), 500

    @app.route("/enrich-data", methods=["POST"])
    async def enrich_all():
        """
        Enriches all loaded cities with coordinates and weather information.

        Returns:
            200 OK: All cities enriched successfully.
            207 Multi-Status: Some cities enriched, some failed.
            500 Internal Server Error: Failed to enrich any data.
        """
        try:
            await data_manager.enrich_with_coordinates_from_api(geo_service)
            await data_manager.enrich_with_weather_from_api(weather_service)

            result = analyze_enrichment_status(data_manager.df)
            enriched_count = int(result['enriched_count'])
            failed_count = int(result['failed_count'])
            failed_cities = list(result['failed_cities'])

            response_body = {
                "message": "Coordinates and weather enrichment completed.",
                "enriched_count": enriched_count,
                "failed_count": failed_count,
                "failed_cities": failed_cities
            }

            if failed_count == 0:
                return jsonify(response_body), 200
            elif enriched_count == 0:
                return jsonify({"error": "Failed to enrich any cities."}), 500
            else:
                return jsonify(response_body), 207  # Multi-Status

        except Exception:
            return jsonify({"error": "Failed to enrich data"}), 500

    @app.route("/add-city", methods=["POST"])
    def add_city():
        """
        Adds a new city to the list and enriches it with coordinates and weather.

        Expects:
            JSON body: { "city_name": "City Name" }

        Returns:
            201 Created: City was added and enriched successfully.
            200 OK: City already exists in the list.
            400 Bad Request: Invalid or missing input.
            424 Failed Dependency: Failed to fetch coordinates or weather.
            500 Internal Server Error: Unexpected failure.
        """
        try:
            data = request.get_json()
            if not data or "city_name" not in data:
                return jsonify({"error": "Missing 'city_name' in request body"}), 400

            city_name = data["city_name"]
            added = data_manager.add_city(city_name)
            total = len(data_manager.df)

            if not added:
                return jsonify({
                    "message": f"City '{city_name}' already exists.",
                    "total_cities": total,
                    "new": False
                }), 200

            # Try to enrich city with coordinates and weather
            success = asyncio.run(enrich_city(city_name))
            if not success:
                data_manager.remove_city(city_name)
                return jsonify({
                    "error": f"Failed to enrich city '{city_name}'. City was not saved."
                }), 424  # Failed Dependency

            return jsonify({
                "message": f"City '{city_name}' added and enriched successfully.",
                "total_cities": len(data_manager.df),
                "new": True
            }), 201

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
                lat=lat,
                lon=lon,
                weather_service=weather_service 
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

            return jsonify({
                "message": f"City '{city_name}' removed successfully.",
                "total_cities": total
            }), 200

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

            file_path = "data/cities.csv"
            data_manager.save_cities_to_csv(file_path)

            return jsonify({
                "message": "City list saved successfully.",
                "file_path": file_path
            }), 200

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
        file_path = "data/cities.csv"

        # If file does not exist, try to save it from memory if available
        if data_manager.df is None or data_manager.df.empty:
            return jsonify({"error": "No data available to export"}), 404

            try:
                data_manager.save_cities_to_csv(file_path)
            except Exception:
                return jsonify({"error": "Failed to save cities before export"}), 500

        # Return the file as an attachment
        return send_file(
            file_path,
            mimetype='text/csv',
            as_attachment=True,
            download_name="cities.csv"
        )