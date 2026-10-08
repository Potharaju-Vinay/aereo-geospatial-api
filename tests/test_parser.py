import pytest

from app.core.exceptions import AppError, ErrorCode
from app.services import parser_service, validation_service
from tests import data_factory


def _parse_zip(zip_path, tmp_path):
    layout = validation_service.validate_shapefile_zip(zip_path.read_bytes())
    shp = validation_service.extract_shapefile(zip_path, layout, tmp_path / "out")
    return parser_service.parse_shapefile(shp)


def test_kml_extracts_all_features_with_types_and_properties(kml_file):
    parsed = parser_service.parse_kml(kml_file)

    assert parsed.crs_label == "EPSG:4326"
    assert [f.geometry_type for f in parsed.features] == ["Polygon", "Polygon", "LineString", "Point"]
    assert parsed.features[0].properties["category"] == "parcel"
    assert parsed.features[0].properties["Name"] == "Plot A"


def test_kml_hides_gdal_rendering_fields(kml_file):
    props = parser_service.parse_kml(kml_file).features[0].properties
    assert "tessellate" not in props and "extrude" not in props


def test_shapefile_wgs84_is_parsed(shapefile_zip, tmp_path):
    parsed = _parse_zip(shapefile_zip, tmp_path)
    assert parsed.crs_label == "EPSG:4326"
    assert parsed.source_crs.is_geographic
    assert len(parsed.features) == 2
    assert parsed.features[1].properties["name"] == "Plot B"


def test_shapefile_projected_crs_is_detected(tmp_path):
    z = data_factory.write_shapefile_zip(tmp_path / "utm.zip", data_factory.sample_features_utm().iloc[:2])
    parsed = _parse_zip(z, tmp_path)
    assert parsed.crs_label == "EPSG:32644"
    assert not parsed.source_crs.is_geographic


def test_shapefile_without_prj_is_rejected_as_missing_crs(tmp_path):
    z = data_factory.write_shapefile_zip(tmp_path / "noprj.zip", include_prj=False)
    with pytest.raises(AppError) as err:
        _parse_zip(z, tmp_path)
    assert err.value.code == ErrorCode.MISSING_CRS
    assert err.value.status_code == 422


def test_empty_geometry_is_reported_not_crashed():
    feature = parser_service.ParsedFeature(index=0, geometry=None, properties={})
    assert feature.geometry_type == parser_service.EMPTY_TYPE
