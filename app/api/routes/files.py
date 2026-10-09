from fastapi import APIRouter, Depends, File, Query, UploadFile
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.exceptions import AppError, ErrorCode
from app.db.database import get_db
from app.db.repositories import FileRepository
from app.schemas.file import FileOut, MeasurementPage
from app.services.file_service import FileService


router = APIRouter(prefix="/api/files", tags=["files"])


@router.post(
    "/",
    response_model=FileOut,
    status_code=201,
    summary="Upload and process a KML or zipped Shapefile",
)
def upload_file(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    settings = get_settings()

    content = file.file.read(
        settings.max_file_size_bytes + 1
    )

    if len(content) > settings.max_file_size_bytes:
        raise AppError(
            413,
            ErrorCode.FILE_TOO_LARGE,
            f"File exceeds the {settings.max_file_size_mb} MB upload limit.",
        )

    return FileService(db).process_upload(
        file.filename or "",
        content,
    )


@router.get(
    "/{file_id}/",
    response_model=FileOut,
    summary="Get information about an uploaded file",
)
def get_file(
    file_id: str,
    db: Session = Depends(get_db),
):
    record = FileRepository(db).get_file(file_id)

    if record is None:
        raise AppError(
            404,
            ErrorCode.FILE_NOT_FOUND,
            f"No file found with id '{file_id}'.",
        )

    return record


@router.get(
    "/{file_id}/measurements/",
    response_model=MeasurementPage,
    summary="Get measurements for an uploaded file",
)
def get_measurements(
    file_id: str,
    geometry_type: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    repository = FileRepository(db)

    record = repository.get_file(file_id)

    if record is None:
        raise AppError(
            404,
            ErrorCode.FILE_NOT_FOUND,
            f"No file found with id '{file_id}'.",
        )

    features, total = repository.list_features(
        file_id=file_id,
        geometry_type=geometry_type,
        page=page,
        page_size=page_size,
    )

    return MeasurementPage(
        items=features,
        page=page,
        page_size=page_size,
        total=total,
    )