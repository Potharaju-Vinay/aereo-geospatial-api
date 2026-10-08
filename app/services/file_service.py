"""Orchestrates the upload flow: validate -> store -> parse -> persist.

Structural problems (wrong type, bad ZIP, missing parts) are rejected before
anything is saved. Once the upload looks structurally sound, a record is
created so later data problems (e.g. missing CRS) are visible via the status
endpoint as FAILED rather than disappearing.
"""
import json
import logging
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path

import shapely
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.exceptions import AppError, ErrorCode
from app.db.models import File, FileStatus
from app.db.repositories import FileRepository
from app.services import parser_service, quality_service, validation_service
from app.services.parser_service import ParsedFile

logger = logging.getLogger(__name__)


def _safe_name(filename: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]", "_", Path(filename).name) or "upload"


def _geometry_to_geojson(geometry) -> dict | None:
    if geometry is None or geometry.is_empty:
        return None
    return json.loads(shapely.to_geojson(geometry))


class FileService:
    def __init__(self, db: Session, settings: Settings | None = None):
        self.settings = settings or get_settings()
        self.repo = FileRepository(db)

    def process_upload(self, filename: str, content: bytes) -> File:
        file_type = validation_service.detect_file_type(filename, self.settings)
        if file_type == "kml":
            validation_service.validate_kml_bytes(content)
            layout = None
        else:
            layout = validation_service.validate_shapefile_zip(content, self.settings)

        file_id = str(uuid.uuid4())
        workdir = self.settings.upload_directory / file_id
        workdir.mkdir(parents=True, exist_ok=True)
        stored = workdir / _safe_name(filename)
        stored.write_bytes(content)

        record = self.repo.create_file(
            id=file_id, filename=Path(filename).name, file_type=file_type,
            status=FileStatus.PROCESSING.value,
        )
        logger.info("upload_started file_id=%s type=%s size=%d", file_id, file_type, len(content))

        try:
            if file_type == "kml":
                parsed = parser_service.parse_kml(stored)
            else:
                shp = validation_service.extract_shapefile(stored, layout, workdir / "extracted", self.settings)
                parsed = parser_service.parse_shapefile(shp)
            return self._persist(record, parsed)
        except AppError as exc:
            logger.warning("upload_failed file_id=%s code=%s", file_id, exc.code.value)
            self.repo.mark_failed(record, exc.code.value, exc.detail)
            raise
        except Exception as exc:  # unexpected: record it, don't leak internals
            logger.exception("upload_crashed file_id=%s", file_id)
            self.repo.mark_failed(record, ErrorCode.PROCESSING_ERROR.value, str(exc))
            raise AppError(500, ErrorCode.PROCESSING_ERROR, "Unexpected error while processing the file.")

    def _persist(self, record: File, parsed: ParsedFile) -> File:
        rows = [
            {
                "feature_index": f.index,
                "geometry_type": f.geometry_type,
                "geometry": _geometry_to_geojson(f.geometry),
                "properties": f.properties,
            }
            for f in parsed.features
        ]
        self.repo.add_features(record.id, rows)

        record.source_crs = parsed.crs_label
        record.feature_count = len(rows)
        record.quality_report = quality_service.build_ingest_report(parsed)
        record.status = FileStatus.COMPLETED.value
        record.completed_at = datetime.now(timezone.utc)
        logger.info("upload_completed file_id=%s features=%d crs=%s", record.id, len(rows), parsed.crs_label)
        return self.repo.save_file(record)
