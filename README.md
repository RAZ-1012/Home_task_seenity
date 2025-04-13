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

### `POST /add-city`
**Add a new city**

**Request Body:**
```json
{ "city_name": "paris" }
```

**Responses:**
- `201 Created`: City added
- `200 OK`: City already exists
- `400 Bad Request`: Missing or invalid city_name
- `500 Internal Server Error`

---

### `DELETE /delete-city/<city_name>`
**Delete a city by name**

**URL Example:**
```
DELETE /delete-city/london
```

**Responses:**
- `200 OK`: City deleted
- `404 Not Found`: City not found
- `422 Unprocessable Entity`: No data loaded
- `500 Internal Server Error`: Deletion failed

---

### `POST /enrich-data`
**Enrich all cities** using:
- OpenCage API for coordinates
- OpenWeather API for weather

**Response (all succeeded):**
```json
{
  "message": "Coordinates and weather enrichment completed.",
  "enriched_count": 5,
  "failed_count": 0,
  "failed_cities": []
}
```

**Partial success:**
- Status code: `207 Multi-Status`  
- Same response format with `failed_cities` > 0

**Errors:**
- `500`: All enrichments failed or unexpected error

---

### `POST /closest-city`
**Find the closest city to a given point**

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

### `GET /get-all-cities`
**Return all current city records**

**Response:**
```json
{
  "cities": [
    { "city_name": "paris", "lat": ..., "weather": ..., ... },
    ...
  ],
  "count": X
}
```

**Notes:**
- Returns **only the current in-memory data** (does not enrich).
- Use `/enrich-data` beforehand if needed.

**Errors:**
- `422 Unprocessable Entity`: No cities loaded
- `500 Internal Server Error`: Failed to retrieve data

---

### `POST /save-cities`
**Save the current in-memory city list to a CSV file (`data/cities.csv`)**

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

If the file does not exist, it attempts to create it from the current in-memory DataFrame.

**Success**: Sends the file `cities.csv`  
**Errors:**
- `404 Not Found`: No file and no in-memory data to create it
- `500 Internal Server Error`: File creation or read failed

---

## ✅ Notes
- All coordinates and weather data are fetched asynchronously using `httpx` and `asyncio`.
- The app maintains the CSV data in memory unless saved explicitly with `/save-cities`.
- The API follows RESTful conventions and returns meaningful status codes for each scenario.