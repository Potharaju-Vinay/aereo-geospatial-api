"""Database tables.

files    one row per uploaded file
features one row per geospatial feature found in that file

Geometry is stored as GeoJSON in the file's *original* CRS, so the API can
return exactly what was uploaded. Measurements are computed separately and
stored alongside, together with how they were produced (provenance).
"""
import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


class FileStatus(str, enum.Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    PARTIAL_SUCCESS = "PARTIAL_SUCCESS"
    FAILED = "FAILED"


class FeatureStatus(str, enum.Enum):
    PENDING = "PENDING"
    MEASURED = "MEASURED"
    NO_MEASUREMENT = "NO_MEASUREMENT"  # e.g. points
    UNSUPPORTED = "UNSUPPORTED"
    ERROR = "ERROR"


class File(Base):
    __tablename__ = "files"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    filename: Mapped[str] = mapped_column(String(255))
    file_type: Mapped[str] = mapped_column(String(20))  # "kml" | "shapefile"
    source_crs: Mapped[str | None] = mapped_column(String(100), nullable=True)
    feature_count: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(20), default=FileStatus.PENDING.value)
    quality_report: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    features: Mapped[list["Feature"]] = relationship(
        back_populates="file", cascade="all, delete-orphan"
    )


class Feature(Base):
    __tablename__ = "features"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    file_id: Mapped[str] = mapped_column(ForeignKey("files.id", ondelete="CASCADE"), index=True)
    feature_index: Mapped[int] = mapped_column(Integer)
    geometry_type: Mapped[str] = mapped_column(String(30))
    geometry: Mapped[dict | None] = mapped_column(JSON, nullable=True)  # GeoJSON, source CRS
    properties: Mapped[dict] = mapped_column(JSON, default=dict)

    # Filled in by the measurement step.
    measurement_type: Mapped[str | None] = mapped_column(String(20), nullable=True)  # area|length
    measurement_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    measurement_unit: Mapped[str | None] = mapped_column(String(10), nullable=True)
    provenance: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    warnings: Mapped[list] = mapped_column(JSON, default=list)

    status: Mapped[str] = mapped_column(String(20), default=FeatureStatus.PENDING.value)
    error_code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    file: Mapped[File] = relationship(back_populates="features")
