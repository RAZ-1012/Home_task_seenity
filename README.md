# City Weather API

A RESTful API to manage, enrich, and retrieve city weather data using Flask, async I/O, and external geolocation and weather services.

---

## 📦 Endpoints

### `GET /`
**Health check**  
Returns a confirmation that the API is up.

**Response:**
```json
{ "message": "City Weather API is running" }
```

---

### `POST /upload-cities`
**Upload a CSV file** (with a column `city_name`)  
**Request Type**: `multipart/form-data`  
**Field Required**: `file`

**Response:**
```json
{ "message": "X cities loaded successfully.", "count": X }
```

**Errors:**
- `400 Bad Request`: Missing file
- `500 Internal Server Error`: Unexpected failure

---

### `POST /upload-and-enrich`
**Upload and immediately enrich cities** (coordinates + weather)  
**Request Type**: `multipart/form-data`  
**Field Required**: `file`

**Success:**
```json
{
  "message": "Upload and enrichment completed successfully.",
  "enriched_count": X,
  "failed_count": 0,
  "failed_cities": []
}
```

**Partial success:**
- Status code: `207 Multi-Status`
- Includes list of failed cities

**Errors:**
- `400 Bad Request`: Missing or invalid file
- `500 Internal Server Error`: Upload or enrichment failed

---

### `POST /add-city`
**Add a single city and enrich it**

**Request Body:**
```json
{ "city_name": "paris" }
```

**Responses:**
- `201 Created`: City added and enriched successfully
- `200 OK`: City already exists
- `424 Failed Dependency`: Enrichment failed; city not saved
- `400 Bad Request`: Invalid or missing city_name
- `500 Internal Server Error`

---

### `POST /enrich-data`
**Enrich all loaded cities** (coordinates + weather)

**Success:**
```json
{
  "message": "Enrichment completed successfully.",
  "enriched_count": X,
  "failed_count": 0,
  "failed_cities": []
}
```

**Partial success:**
- Status code: `207 Multi-Status`
- Response includes `failed_cities`

**Errors:**
- `422 Unprocessable Entity`: No cities loaded
- `500 Internal Server Error`: Unexpected failure

---

### `POST /closest-city`
**Find the closest city to a given point**  
Fetches weather if missing.

**Request Body:**
```json
{ "lat": 32.08, "lon": 34.78 }
```

**Response:**
```json
{
  "city_name": "tel aviv",
  "distance_km": 4.2,
  "weather": "clear sky",
  "temperature": 26.5
}
```

**Errors:**
- `400 Bad Request`: Invalid or missing coordinates
- `422 Unprocessable Entity`: No cities loaded
- `500 Internal Server Error`: Processing failed

---

### `DELETE /delete-city/<city_name>`
**Delete a city by name**

**Example:**
```
DELETE /delete-city/london
```

**Responses:**
- `200 OK`: City deleted
- `404 Not Found`: City not found
- `422 Unprocessable Entity`: No data loaded
- `500 Internal Server Error`: Deletion failed

---

### `GET /get-all-cities`
**Return all city records as JSON**

**Response:**
```json
{
  "cities": [
    { "city_name": "paris", "latitude": ..., "weather": ..., ... },
    ...
  ],
  "count": X
}
```

**Notes:**
- Returns in-memory data only
- Does not enrich automatically

**Errors:**
- `422 Unprocessable Entity`: No data loaded
- `500 Internal Server Error`: Retrieval failed

---

### `POST /save-cities`
**Save the current city list to a CSV file**  
(File path is configurable via `.env` under `CITIES_CSV_PATH`)

**Response:**
```json
{
  "message": "City list saved successfully.",
  "file_path": "data/cities.csv"
}
```

**Errors:**
- `422 Unprocessable Entity`: No data to save
- `500 Internal Server Error`: Save failed

---

### `GET /export-cities`
**Download the saved CSV file**

If the file does not exist, attempts to create it from memory.

**Success**: Sends the file as download  
**Errors:**
- `404 Not Found`: No in-memory data to export
- `500 Internal Server Error`: File creation or read failed

---

## ✅ Notes
- All enrichment (coordinates + weather) is done asynchronously using `httpx` and `asyncio`.
- The app keeps cities in memory and saves explicitly via `/save-cities`.
- File path for saving is controlled by the environment variable `CITIES_CSV_PATH`.
- The API follows RESTful standards and returns appropriate status codes.