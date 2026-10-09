import pytest
from pyproj import CRS
from shapely.geometry import LineString, Polygon

from app.services.crs_service import select_projected_crs


def test_geographic_coordinates_select_utm_for_hyderabad():
    geometry = LineString([
        (78.48, 17.36),
        (78.49, 17.37),
    ])

    result = select_projected_crs(geometry, CRS.from_epsg(4326))

    assert result.source_crs == "EPSG:4326"
    assert result.projected_crs == "EPSG:32644"
    assert result.method == "utm_from_centroid"


def test_metric_projected_crs_is_preserved():
    geometry = LineString([
        (250000, 1920000),
        (250100, 1920100),
    ])

    result = select_projected_crs(geometry, CRS.from_epsg(32644))

    assert result.source_crs == "EPSG:32644"
    assert result.projected_crs == "EPSG:32644"
    assert result.method == "source_projected_crs"


def test_empty_geometry_is_rejected():
    with pytest.raises(ValueError, match="non-empty geometry"):
        select_projected_crs(
            LineString(),
            CRS.from_epsg(4326),
        )


def test_polar_geometry_outside_utm_range_is_rejected():
    geometry = Polygon([
        (10, 85),
        (11, 85),
        (11, 86),
        (10, 86),
        (10, 85),
    ])

    with pytest.raises(ValueError, match="standard UTM latitude range"):
        select_projected_crs(geometry, CRS.from_epsg(4326))


def test_missing_source_crs_is_rejected():
    with pytest.raises(ValueError, match="Source CRS is required"):
        select_projected_crs(
            LineString([(78.48, 17.36), (78.49, 17.37)]),
            None,
        )