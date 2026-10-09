# GeoMeasure - Trusted Geospatial Measurement API

GeoMeasure is a Python REST API that processes KML files and zipped Shapefiles, calculates geometry measurements, and provides measurement provenance and data quality reports.

The goal is to make geospatial measurements more transparent by recording the coordinate reference systems (CRS) and independent geodesic cross-checks used to produce each result.

## Features

- Upload KML files and ZIP archives containing a Shapefile.
- Calculate polygon and multipolygon areas in square metres.
- Calculate line and multiline lengths in metres.
- Preserve point features without calculating area or length.
- Detect and report geometry types, feature properties, and CRS information.
- Transform geographic coordinates to an appropriate projected CRS before measuring.
- Provide geodesic cross-checks and percentage differences.
- Report geometry repairs, measurement warnings, and data quality information.
- Store file and feature metadata using SQLAlchemy and SQLite.
- Support measurement filtering and pagination.
- Validate uploaded files and return structured errors.

## Technology Stack

- **Language:** Python
- **API framework:** FastAPI
- **Geospatial processing:** GeoPandas, Shapely, PyProj, Pyogrio
- **Database:** SQLite with SQLAlchemy
- **Testing:** Pytest and FastAPI TestClient

## Quick Start

### Prerequisites

- Python 3.11 or later
- Git

### 1. Clone the repository

```bash
git clone https://github.com/Potharaju-Vinay/aereo-geospatial-api.git
cd aereo-geospatial-api
```

### 2. Create a virtual environment

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Linux or macOS:

```bash
python -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

```bash
python -m pip install -r requirements.txt
```

### 4. Configure the environment

Copy `.env.example` to `.env` and configure the available application settings as needed.

Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

Linux or macOS:

```bash
cp .env.example .env
```

### 5. Start the API

```bash
python -m uvicorn app.main:app --reload
```

Open the interactive API documentation:

http://127.0.0.1:8000/docs

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/files/` | Upload and process a KML or zipped Shapefile |
| GET | `/api/files/{file_id}/` | Retrieve file metadata and its quality report |
| GET | `/api/files/{file_id}/measurements/` | Retrieve feature geometries and measurement results |
| GET | `/health` | Check API health |

### Upload a file

Send a multipart form request to `POST /api/files/` using the file upload field exposed in Swagger UI.

Supported inputs:

- `.kml`
- `.zip` containing one Shapefile with its required component files

Example using cURL:

```bash
curl -X POST "http://127.0.0.1:8000/api/files/" \
  -F "file=@sample_data/sample.kml"
```

The response includes the file ID, detected file type, CRS, processing status, feature count, and quality report.

### Retrieve file details

```bash
curl "http://127.0.0.1:8000/api/files/{file_id}/"
```

Example response (selected fields):

```json
{
  "id": "11b9686d-2ce2-453c-9944-e7f718ed2974",
  "filename": "ne_10m_admin_0_countries.zip",
  "file_type": "shapefile",
  "crs": "EPSG:4326",
  "status": "COMPLETED",
  "feature_count": 258,
  "error_code": null,
  "error_message": null
}
```

The example shows selected fields from a successful upload. The complete response also includes the file's quality report and processing timestamps.


### Retrieve measurements

```bash
curl "http://127.0.0.1:8000/api/files/{file_id}/measurements/"
```

Optional query parameters:

| Parameter | Description |
|---|---|
| `geometry_type` | Filter features by geometry type |
| `page` | Page number, starting at 1 |
| `page_size` | Number of records per page, up to 100 |

Example:

```bash
curl "http://127.0.0.1:8000/api/files/{file_id}/measurements/?geometry_type=Polygon&page=1&page_size=10"
```

## Measurement and CRS Handling

Geographic coordinates such as EPSG:4326 use angular units (degrees), so they must not be used directly to calculate areas or distances in metres.

GeoMeasure follows this process:

1. Read the source CRS from the uploaded data. KML uses EPSG:4326; Shapefiles must provide a valid CRS.
2. Select a suitable projected CRS based on the geometry's location and geographic extent. UTM is used where appropriate, while large or global geometries require a projection better suited to their extent.
3. Transform the geometry into the selected projected CRS.
4. Calculate polygon area or line length using the projected geometry.
5. Calculate an independent geodesic cross-check using PyProj.
6. Record the projected CRS, geodesic result, percentage difference, and applicable warnings.

Projection selection matters because no single local projection is appropriate for every geographic extent. Large or global geometries can produce differences between projected and geodesic measurements, so GeoMeasure records cross-check results and warnings to support interpretation.

## Measurement Results

Each feature result can include:

- Feature ID and index
- Geometry type and GeoJSON geometry
- Feature properties
- Measurement type, value, and unit
- Source and projected CRS information
- Geodesic cross-check and percentage difference
- Warnings, status, and structured error details

Polygon measurements use square metres (`m2`), and line measurements use metres (`m`). Point features return `NO_MEASUREMENT`.

Invalid geometries may be repaired before measurement, with the repair recorded in the result. Unsupported or problematic features are represented using their feature status and error information where applicable.

### Example Measurement Result

The following example shows selected fields returned for a measured feature:

```json
{
  "id": 4200,
  "feature_index": 0,
  "geometry_type": "MultiPolygon",
  "measurement_type": "area",
  "measurement_value": 1879826219056.2422,
  "measurement_unit": "m2",
  "status": "MEASURED",
  "warnings": [
    "Large polygon: using a global equal-area projection."
  ]
}
```

This example is taken from a successful measurement response. Geometry coordinates and feature properties are omitted for readability. Source and projected CRS fields are also omitted because they were not populated in the displayed result.


## Data Quality Reports

The file-level quality report summarizes:

- Source CRS and whether it is geographic
- Total feature count and geometry type distribution
- Measurable and no-measurement features
- Unsupported and empty geometries
- Features with missing properties
- Geometry repairs
- Measurement errors and warnings

## Architecture

The application separates API handling, business logic, geospatial processing, and persistence.

```text
Client
  |
FastAPI Routes
  |
File Service
  |-- Validation Service
  |-- Parser Service
  |-- CRS Service
  |-- Measurement Service
  |-- Quality Service
  |
Repository Layer
  |
SQLAlchemy / SQLite
```

Uploaded files are validated, parsed, processed, and stored with their associated feature metadata and measurement results.

## Error Handling

The API returns structured error responses containing an error code and detail message.

Example:

```json
{
  "error": "MISSING_CRS",
  "detail": "The uploaded dataset does not contain a valid CRS."
}
```

Clients should inspect the returned HTTP status code and error code to determine the appropriate action.

## Running Tests

Run the automated test suite:

```bash
python -m pytest -v
```

The current test suite covers upload API behavior, validation, parsing, and measurement service behavior.

## Design Decisions and Trade-offs

- **FastAPI:** Provides a lightweight API framework and interactive API documentation.
- **SQLite:** Keeps local development and evaluation simple. A production deployment may use PostgreSQL with PostGIS.
- **Projected measurements:** Avoid calculating metric areas and lengths directly from geographic degrees.
- **Geodesic cross-checks:** Provide additional evidence for assessing measurement differences.
- **Synchronous processing:** Keeps the assignment implementation straightforward. Background workers could be introduced for large datasets.
- **Feature-level results:** Preserve information about individual features rather than exposing only aggregate measurements.

## Future Improvements

- Broader support for large and multi-zone datasets
- More extensive geospatial edge-case testing
- PostgreSQL/PostGIS integration
- Background processing for large uploads
- Additional export formats and measurement units
- Continuous integration and containerized deployment

## Frontend Dashboard

GeoMeasure includes a React and TypeScript dashboard for uploading datasets, exploring geometries on an interactive map, reviewing measurements, and inspecting quality reports.

### Run the frontend

Open a second terminal from the repository root:

```powershell
cd frontend
npm install
npm run dev
```

Open the local URL displayed by Vite, usually `http://localhost:5173`.

Keep the FastAPI backend running in the first terminal. Its interactive API documentation is available at `http://127.0.0.1:8000/docs`.

### Frontend validation

Build the frontend for production:

```powershell
npm run build
```

Run the frontend lint checks:

```powershell
npm run lint
```



## Learning Outcomes

This project demonstrates REST API development, input validation, geospatial parsing, coordinate transformations, measurement calculations, persistence, error handling, and automated testing.

Repository: https://github.com/Potharaju-Vinay/aereo-geospatial-api
