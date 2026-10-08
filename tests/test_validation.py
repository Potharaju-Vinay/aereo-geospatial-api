import io
import zipfile

import pytest

from app.core.config import get_settings
from app.core.exceptions import AppError, ErrorCode
from app.services import validation_service as v


def _zip_bytes(entries: dict[str, bytes]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, data in entries.items():
            zf.writestr(name, data)
    return buf.getvalue()


def _code(exc_info) -> ErrorCode:
    return exc_info.value.code


def test_unsupported_extension_is_rejected():
    with pytest.raises(AppError) as err:
        v.detect_file_type("notes.txt")
    assert _code(err) == ErrorCode.UNSUPPORTED_FILE_TYPE
    assert err.value.status_code == 400


@pytest.mark.parametrize("name,expected", [("a.kml", "kml"), ("A.KML", "kml"), ("b.zip", "shapefile")])
def test_supported_extensions(name, expected):
    assert v.detect_file_type(name) == expected


def test_empty_or_non_kml_content_is_rejected():
    for bad in (b"", b"   ", b"just some text"):
        with pytest.raises(AppError) as err:
            v.validate_kml_bytes(bad)
        assert _code(err) == ErrorCode.INVALID_FILE_CONTENT


def test_non_zip_bytes_are_rejected():
    with pytest.raises(AppError) as err:
        v.validate_shapefile_zip(b"this is not a zip")
    assert _code(err) == ErrorCode.INVALID_ZIP


def test_path_traversal_entry_is_rejected():
    evil = _zip_bytes({"../../etc/evil.shp": b"x", "a.shx": b"x", "a.dbf": b"x"})
    with pytest.raises(AppError) as err:
        v.validate_shapefile_zip(evil)
    assert _code(err) == ErrorCode.INVALID_ZIP


def test_absolute_path_entry_is_rejected():
    with pytest.raises(AppError) as err:
        v.validate_shapefile_zip(_zip_bytes({"/tmp/a.shp": b"x"}))
    assert _code(err) == ErrorCode.INVALID_ZIP


def test_zip_without_shp_is_rejected():
    with pytest.raises(AppError) as err:
        v.validate_shapefile_zip(_zip_bytes({"readme.txt": b"hello"}))
    assert _code(err) == ErrorCode.MISSING_SHAPEFILE_COMPONENT


@pytest.mark.parametrize("present,missing", [
    ({"a.shp": b"x", "a.dbf": b"x"}, ".shx"),
    ({"a.shp": b"x", "a.shx": b"x"}, ".dbf"),
])
def test_missing_required_component_is_named(present, missing):
    with pytest.raises(AppError) as err:
        v.validate_shapefile_zip(_zip_bytes(present))
    assert _code(err) == ErrorCode.MISSING_SHAPEFILE_COMPONENT
    assert missing in err.value.detail


def test_two_shapefiles_in_one_zip_are_rejected():
    parts = {f"{s}{e}": b"x" for s in ("a", "b") for e in (".shp", ".shx", ".dbf")}
    with pytest.raises(AppError) as err:
        v.validate_shapefile_zip(_zip_bytes(parts))
    assert _code(err) == ErrorCode.INVALID_ZIP


def test_zip_bomb_is_rejected_by_uncompressed_size():
    settings = get_settings().model_copy(update={"max_uncompressed_size_mb": 1})
    bomb = _zip_bytes({"a.shp": b"\0" * (3 * 1024 * 1024), "a.shx": b"x", "a.dbf": b"x"})
    assert len(bomb) < 100_000  # tiny on the wire, huge once expanded
    with pytest.raises(AppError) as err:
        v.validate_shapefile_zip(bomb, settings)
    assert _code(err) == ErrorCode.FILE_TOO_LARGE
    assert err.value.status_code == 413


def test_too_many_entries_are_rejected():
    settings = get_settings().model_copy(update={"max_zip_entries": 3})
    many = _zip_bytes({f"f{i}.txt": b"x" for i in range(10)})
    with pytest.raises(AppError) as err:
        v.validate_shapefile_zip(many, settings)
    assert _code(err) == ErrorCode.INVALID_ZIP


def test_macos_metadata_is_ignored():
    zipped = _zip_bytes({
        "a.shp": b"x", "a.shx": b"x", "a.dbf": b"x",
        "__MACOSX/._a.shp": b"junk", "sub/._a.dbf": b"junk",
    })
    assert v.validate_shapefile_zip(zipped).stem == "a"


def test_extraction_writes_only_whitelisted_parts(tmp_path):
    zip_path = tmp_path / "in.zip"
    zip_path.write_bytes(_zip_bytes({
        "data/a.shp": b"1", "data/a.shx": b"2", "data/a.dbf": b"3", "data/a.prj": b"4",
        "data/malware.exe": b"nope",
    }))
    layout = v.validate_shapefile_zip(zip_path.read_bytes())
    shp = v.extract_shapefile(zip_path, layout, tmp_path / "out")

    assert shp.name == "a.shp"
    assert sorted(p.name for p in (tmp_path / "out").iterdir()) == ["a.dbf", "a.prj", "a.shp", "a.shx"]
