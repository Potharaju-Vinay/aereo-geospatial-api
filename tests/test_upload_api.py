import uuid

from app.core.config import get_settings
from app.db.models import File
from app.db.repositories import FileRepository
from tests import data_factory


def _upload(client, path, name=None, content=None):
    data = content if content is not None else path.read_bytes()
    return client.post("/api/files/", files={"file": (name or path.name, data)})


def test_health(client):
    assert client.get("/health").json() == {"status": "healthy"}


def test_upload_kml_creates_completed_file(client, kml_file):
    r = _upload(client, kml_file)
    assert r.status_code == 201
    body = r.json()
    assert body["filename"] == "survey.kml"
    assert body["file_type"] == "kml"
    assert body["feature_count"] == 4
    assert body["crs"] == "EPSG:4326"
    assert body["status"] == "COMPLETED"
    uuid.UUID(body["id"])  # valid id


def test_upload_shapefile_zip(client, shapefile_zip):
    body = _upload(client, shapefile_zip).json()
    assert body["file_type"] == "shapefile"
    assert body["feature_count"] == 2
    assert body["status"] == "COMPLETED"


def test_ingest_quality_report_counts_geometry_types(client, kml_file):
    report = _upload(client, kml_file).json()["quality_report"]
    assert report["geometry_types"] == {"Polygon": 2, "LineString": 1, "Point": 1}
    assert report["measurable_features"] == 3
    assert report["no_measurement_features"] == 1
    assert report["empty_geometries"] == 0


def test_file_info_matches_upload(client, kml_file):
    created = _upload(client, kml_file).json()
    info = client.get(f"/api/files/{created['id']}/")
    assert info.status_code == 200
    assert info.json()["id"] == created["id"]
    assert info.json()["feature_count"] == 4


def test_unknown_file_id_returns_404_with_code(client):
    r = client.get("/api/files/does-not-exist/")
    assert r.status_code == 404
    assert r.json()["error"] == "FILE_NOT_FOUND"


def test_unsupported_extension_returns_400(client):
    r = client.post("/api/files/", files={"file": ("notes.txt", b"hello")})
    assert r.status_code == 400
    assert r.json()["error"] == "UNSUPPORTED_FILE_TYPE"


def test_missing_file_field_returns_structured_422(client):
    r = client.post("/api/files/")
    assert r.status_code == 422
    assert r.json()["error"] == "VALIDATION_ERROR"


def test_oversized_upload_returns_413(client, kml_file, monkeypatch):
    monkeypatch.setattr(get_settings(), "max_file_size_mb", 0)
    r = _upload(client, kml_file)
    assert r.status_code == 413
    assert r.json()["error"] == "FILE_TOO_LARGE"


def test_corrupt_zip_returns_422_and_nothing_is_saved(client, db):
    r = client.post("/api/files/", files={"file": ("bad.zip", b"not a zip")})
    assert r.status_code == 422
    assert r.json()["error"] == "INVALID_ZIP"
    assert db.query(File).count() == 0


def test_zip_missing_shx_returns_422_with_component_name(client, tmp_path):
    z = data_factory.write_shapefile_zip(tmp_path / "x.zip", include_shx=False)
    r = _upload(client, z)
    assert r.status_code == 422
    assert r.json()["error"] == "MISSING_SHAPEFILE_COMPONENT"
    assert ".shx" in r.json()["detail"]


def test_missing_crs_is_recorded_as_failed_file(client, db, tmp_path):
    z = data_factory.write_shapefile_zip(tmp_path / "noprj.zip", include_prj=False)
    r = _upload(client, z)
    assert r.status_code == 422
    assert r.json()["error"] == "MISSING_CRS"

    record = db.query(File).one()
    assert record.status == "FAILED"
    assert record.error_code == "MISSING_CRS"
    # the failure is visible through the status endpoint too
    info = client.get(f"/api/files/{record.id}/").json()
    assert info["status"] == "FAILED" and info["error_code"] == "MISSING_CRS"


def test_features_are_persisted_with_geojson_and_properties(client, db, kml_file):
    file_id = _upload(client, kml_file).json()["id"]
    features = FileRepository(db).get_features(file_id)
    assert [f.geometry_type for f in features] == ["Polygon", "Polygon", "LineString", "Point"]
    assert features[0].geometry["type"] == "Polygon"
    assert features[0].properties["Name"] == "Plot A"


def test_repository_pagination_and_filtering(client, db, kml_file):
    file_id = _upload(client, kml_file).json()["id"]
    repo = FileRepository(db)

    page1, total = repo.list_features(file_id, page=1, page_size=3)
    page2, _ = repo.list_features(file_id, page=2, page_size=3)
    assert total == 4 and len(page1) == 3 and len(page2) == 1

    polygons, poly_total = repo.list_features(file_id, geometry_type="Polygon")
    assert poly_total == 2 and all(f.geometry_type == "Polygon" for f in polygons)
