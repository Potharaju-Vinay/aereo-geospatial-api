# GeoMeasure Frontend

A React and TypeScript dashboard for uploading geospatial files, exploring geometries on an interactive map, reviewing measurement results, and inspecting data quality and processing provenance.

## Tech Stack

- React 19
- TypeScript
- Vite
- React Leaflet and Leaflet
- Lucide React

## Prerequisites

- Node.js and npm
- GeoMeasure FastAPI backend

## Installation

From the project root, navigate to the frontend directory and install dependencies:

```powershell
cd frontend
npm install
```

## Run the Development Server

```powershell
npm run dev
```

Open the local URL displayed by Vite, usually `http://localhost:5173`.

## Run the Backend

In a separate terminal, navigate to the project root and activate the Python virtual environment:

```powershell
.\.venv\Scripts\Activate.ps1
python -m uvicorn app.main:app --reload
```

Backend URL: `http://127.0.0.1:8000`

Interactive API documentation: `http://127.0.0.1:8000/docs`

The backend command assumes the application entry point is `app.main:app`.

## Features

- Upload KML and zipped Shapefile datasets
- View dataset metadata and processing status
- Explore geometries on an interactive map
- Inspect feature properties and geometry details
- Browse paginated measurement results
- Review geometry quality reports and processing provenance

## Available Scripts

| Command | Description |
|---|---|
| `npm run dev` | Start the development server |
| `npm run build` | Type-check and build for production |
| `npm run lint` | Run ESLint |
| `npm run preview` | Preview the production build |

## Production Build

```powershell
npm run build
```

The production build is generated in the `dist` directory.

## Project Structure

```text
frontend/
├── public/
├── src/
├── package.json
├── package-lock.json
├── tsconfig.json
└── vite.config.ts
```

## Related Documentation

See the main README in the repository root for backend architecture, API endpoints, measurement methodology, CRS handling, validation, and design decisions.