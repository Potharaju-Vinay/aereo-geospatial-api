"""Upload validation and safe ZIP handling.

We never blindly extract an uploaded ZIP. Before touching the disk we check:
  * it is really a ZIP
  * entry count and total *uncompressed* size are within limits (zip bombs)
  * no entry tries to escape the target folder (path traversal / zip-slip)
  * it contains exactly one shapefile with its required .shx and .dbf parts
Only whitelisted shapefile component files are extracted, each written under
a name we choose ourselves.
"""
import io
import zipfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from app.core.config import Settings, get_settings
from app.core.exceptions import AppError, ErrorCode

REQUIRED_PARTS = (".shp", ".shx", ".dbf")
ALLOWED_PARTS = {".shp", ".shx", ".dbf", ".prj", ".cpg", ".qpj", ".sbn", ".sbx"}
KML_SNIFF_BYTES = 4096


@dataclass
class ShapefileLayout:
    """What we found inside a validated ZIP."""

    stem: str  # shapefile base name, e.g. "survey"
    members: dict[str, str]  # extension -> original ZIP entry name


def detect_file_type(filename: str, settings: Settings | None = None) -> str:
    settings = settings or get_settings()
    suffix = Path(filename or "").suffix.lower()
    if suffix not in settings.allowed_extensions:
        raise AppError(
            400,
            ErrorCode.UNSUPPORTED_FILE_TYPE,
            "Only .kml files and .zip files containing a Shapefile are supported.",
        )
    return "kml" if suffix == ".kml" else "shapefile"


def validate_kml_bytes(content: bytes) -> None:
    """Cheap sanity check that the upload really looks like KML."""
    head = content[:KML_SNIFF_BYTES].lower()
    if not content.strip() or b"<kml" not in head:
        raise AppError(
            422, ErrorCode.INVALID_FILE_CONTENT, "The file does not look like a valid KML document."
        )


def _is_unsafe_path(name: str) -> bool:
    normalized = name.replace("\\", "/")
    parts = PurePosixPath(normalized).parts
    return normalized.startswith("/") or ".." in parts or (len(normalized) > 1 and normalized[1] == ":")


def _is_ignorable(name: str) -> bool:
    """Directories and macOS metadata that carry no data."""
    normalized = name.replace("\\", "/")
    base = PurePosixPath(normalized).name
    return normalized.endswith("/") or normalized.startswith("__MACOSX/") or base.startswith("._")


def validate_shapefile_zip(content: bytes, settings: Settings | None = None) -> ShapefileLayout:
    settings = settings or get_settings()
    try:
        zf = zipfile.ZipFile(io.BytesIO(content))
    except zipfile.BadZipFile:
        raise AppError(422, ErrorCode.INVALID_ZIP, "The uploaded file is not a valid ZIP archive.")

    with zf:
        infos = zf.infolist()
        if len(infos) > settings.max_zip_entries:
            raise AppError(
                422, ErrorCode.INVALID_ZIP,
                f"ZIP contains too many entries (limit {settings.max_zip_entries}).",
            )

        total_size = 0
        by_stem: dict[str, dict[str, str]] = {}
        for info in infos:
            if _is_unsafe_path(info.filename):
                raise AppError(
                    422, ErrorCode.INVALID_ZIP,
                    "ZIP contains an unsafe file path and was rejected.",
                )
            if _is_ignorable(info.filename):
                continue
            total_size += info.file_size
            if total_size > settings.max_uncompressed_bytes:
                raise AppError(
                    413, ErrorCode.FILE_TOO_LARGE,
                    f"ZIP expands beyond the {settings.max_uncompressed_size_mb} MB limit.",
                )
            path = PurePosixPath(info.filename.replace("\\", "/"))
            ext = path.suffix.lower()
            if ext in ALLOWED_PARTS:
                by_stem.setdefault(path.stem, {})[ext] = info.filename

    shapefiles = [stem for stem, parts in by_stem.items() if ".shp" in parts]
    if not shapefiles:
        raise AppError(
            422, ErrorCode.MISSING_SHAPEFILE_COMPONENT, "ZIP does not contain a .shp file."
        )
    if len(shapefiles) > 1:
        raise AppError(
            422, ErrorCode.INVALID_ZIP,
            "ZIP must contain exactly one Shapefile; found " + str(len(shapefiles)) + ".",
        )

    stem = shapefiles[0]
    missing = [ext for ext in REQUIRED_PARTS if ext not in by_stem[stem]]
    if missing:
        raise AppError(
            422, ErrorCode.MISSING_SHAPEFILE_COMPONENT,
            f"Shapefile is missing required component(s): {', '.join(missing)}.",
        )
    return ShapefileLayout(stem=stem, members=by_stem[stem])


def extract_shapefile(
    zip_path: Path, layout: ShapefileLayout, dest_dir: Path, settings: Settings | None = None
) -> Path:
    """Extract only the whitelisted parts, under names we choose. Returns the .shp path.

    The copy loop counts the bytes actually written, because a ZIP's header
    can lie about the uncompressed size.
    """
    settings = settings or get_settings()
    dest_dir.mkdir(parents=True, exist_ok=True)
    written = 0
    with zipfile.ZipFile(zip_path) as zf:
        for ext, member in layout.members.items():
            target = dest_dir / f"{layout.stem}{ext}"
            with zf.open(member) as src, open(target, "wb") as out:
                while chunk := src.read(1024 * 1024):
                    written += len(chunk)
                    if written > settings.max_uncompressed_bytes:
                        raise AppError(
                            413, ErrorCode.FILE_TOO_LARGE,
                            "ZIP expands beyond the allowed size while extracting.",
                        )
                    out.write(chunk)
    return dest_dir / f"{layout.stem}.shp"
