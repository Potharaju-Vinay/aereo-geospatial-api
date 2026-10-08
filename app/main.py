from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.api.routes import files
from app.core.config import get_settings
from app.core.exceptions import AppError, ErrorCode
from app.core.logging import configure_logging
from app.db.database import init_db

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging(settings.log_level)
    settings.upload_directory.mkdir(parents=True, exist_ok=True)
    init_db()
    yield


app = FastAPI(
    title="GeoMeasure",
    description="Upload a KML or zipped Shapefile and get CRS-correct measurements.",
    version="0.1.0",
    lifespan=lifespan,
)


@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError):
    return JSONResponse(status_code=exc.status_code, content=exc.to_dict())


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError):
    first = exc.errors()[0] if exc.errors() else {}
    where = ".".join(str(p) for p in first.get("loc", []) if p != "body")
    detail = f"{where}: {first.get('msg', 'invalid request')}" if where else "Invalid request."
    return JSONResponse(
        status_code=422, content={"error": ErrorCode.VALIDATION_ERROR.value, "detail": detail}
    )


@app.get("/health", tags=["system"])
def health():
    return {"status": "healthy"}


app.include_router(files.router)
