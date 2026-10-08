from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.exceptions import AppError, ErrorCode
from app.db.database import get_db
from app.db.repositories import FileRepository
from app.schemas.file import FileOut
from app.services.file_service import FileService

router = APIRouter(prefix="/api/files", tags=["files"])


@router.post("/", response_model=FileOut, status_code=201, summary="Upload and process a KML or zipped Shapefile")
def upload_file(file: UploadFile = File(...), db: Session = Depends(get_db)):
    settings = get_settings()
    # Read one byte past the limit so oversized uploads are detected without
    # loading an arbitrarily large body into memory.
    content = file.file.read(settings.max_file_size_bytes + 1)
    if len(content) > settings.max_file_size_bytes:
        raise AppError(
            413, ErrorCode.FILE_TOO_LARGE,
            f"File exceeds the {settings.max_file_size_mb} MB upload limit.",
        )
    return FileService(db).process_upload(file.filename or "", content)


@router.get("/{file_id}/", response_model=FileOut, summary="Get information about an uploaded file")
def get_file(file_id: str, db: Session = Depends(get_db)):
    record = FileRepository(db).get_file(file_id)
    if record is None:
        raise AppError(404, ErrorCode.FILE_NOT_FOUND, f"No file found with id '{file_id}'.")
    return record
