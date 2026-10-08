# GeoMeasure

Upload a **KML** or a **zipped Shapefile** and get CRS-correct measurements for every feature.

> Status: Day 1 of build. Upload, validation, parsing and storage are done.
> CRS selection and measurements arrive next. Full documentation is written at the end.

## Quick start

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```

Open http://127.0.0.1:8000/docs for the interactive API docs.

## Run the tests

```bash
pytest
```

## Endpoints so far

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/files/` | Upload a `.kml` or a `.zip` containing a Shapefile |
| GET | `/api/files/{id}/` | File info, status and data quality report |
| GET | `/health` | Liveness check |

Errors always look like `{"error": "MISSING_CRS", "detail": "..."}`.
