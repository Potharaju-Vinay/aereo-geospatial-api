from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class FileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    filename: str
    file_type: str
    feature_count: int
    crs: str | None = Field(default=None, validation_alias="source_crs")
    status: str
    quality_report: dict | None = None
    error_code: str | None = None
    error_message: str | None = None
    created_at: datetime
    completed_at: datetime | None = None


class MeasurementOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    feature_index: int
    geometry_type: str
    geometry: dict | None
    properties: dict

    measurement_type: str | None
    measurement_value: float | None
    measurement_unit: str | None

    provenance: dict | None
    warnings: list

    status: str
    error_code: str | None
    error_message: str | None


class MeasurementPage(BaseModel):
    items: list[MeasurementOut]
    page: int
    page_size: int
    total: int