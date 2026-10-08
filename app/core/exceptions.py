"""Structured API errors.

Every failure the API reports carries a stable machine-readable code
(``error``) plus a human-readable ``detail``. Clients can branch on the code
without parsing messages.
"""
from enum import Enum


class ErrorCode(str, Enum):
    UNSUPPORTED_FILE_TYPE = "UNSUPPORTED_FILE_TYPE"
    FILE_TOO_LARGE = "FILE_TOO_LARGE"
    INVALID_FILE_CONTENT = "INVALID_FILE_CONTENT"
    INVALID_ZIP = "INVALID_ZIP"
    MISSING_SHAPEFILE_COMPONENT = "MISSING_SHAPEFILE_COMPONENT"
    MISSING_CRS = "MISSING_CRS"
    NO_FEATURES = "NO_FEATURES"
    INVALID_GEOMETRY = "INVALID_GEOMETRY"
    EMPTY_GEOMETRY = "EMPTY_GEOMETRY"
    UNSUPPORTED_GEOMETRY = "UNSUPPORTED_GEOMETRY"
    FILE_NOT_FOUND = "FILE_NOT_FOUND"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    PROCESSING_ERROR = "PROCESSING_ERROR"


class AppError(Exception):
    """An expected, client-facing error with an HTTP status and a code."""

    def __init__(self, status_code: int, code: ErrorCode, detail: str):
        super().__init__(detail)
        self.status_code = status_code
        self.code = code
        self.detail = detail

    def to_dict(self) -> dict:
        return {"error": self.code.value, "detail": self.detail}
