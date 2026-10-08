"""Repository: the only place that talks to SQLAlchemy queries.

Services call these methods and never write queries themselves, so the
business logic stays independent of how data is stored.
"""
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import Feature, File, FileStatus


class FileRepository:
    def __init__(self, db: Session):
        self.db = db

    # ---- files -----------------------------------------------------
    def create_file(self, **fields) -> File:
        record = File(**fields)
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        return record

    def get_file(self, file_id: str) -> File | None:
        return self.db.get(File, file_id)

    def save_file(self, record: File) -> File:
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        return record

    def mark_failed(self, record: File, code: str, message: str) -> File:
        record.status = FileStatus.FAILED.value
        record.error_code = code
        record.error_message = message
        record.completed_at = datetime.now(timezone.utc)
        return self.save_file(record)

    # ---- features --------------------------------------------------
    def add_features(self, file_id: str, rows: list[dict]) -> None:
        """Insert all features of a file in one transaction."""
        self.db.add_all([Feature(file_id=file_id, **row) for row in rows])
        self.db.commit()

    def get_features(self, file_id: str) -> list[Feature]:
        stmt = select(Feature).where(Feature.file_id == file_id).order_by(Feature.feature_index)
        return list(self.db.scalars(stmt))

    def list_features(
        self,
        file_id: str,
        geometry_type: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Feature], int]:
        """Paginated features of a file, optionally filtered by geometry type."""
        base = select(Feature).where(Feature.file_id == file_id)
        if geometry_type:
            base = base.where(Feature.geometry_type == geometry_type)

        total = self.db.scalar(select(func.count()).select_from(base.subquery())) or 0
        stmt = (
            base.order_by(Feature.feature_index)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return list(self.db.scalars(stmt)), total
