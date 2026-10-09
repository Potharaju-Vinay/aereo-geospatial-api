from pyproj import CRS
from shapely.geometry import LineString, Point, Polygon

from app.services.measurement_service import measure_geometry


def test_linestring_measurement():
    geometry = LineString([
        (78.4770, 17.3850),
        (78.4860, 17.3850),
    ])

    result = measure_geometry(
        geometry,
        CRS.from_epsg(4326),
    )

    assert result.status == "MEASURED"
    assert result.measurement_type == "length"
    assert result.unit == "m"
    assert result.value > 900
    assert result.geodesic_value > 900
    assert result.difference_percent < 0.5
    assert result.projected_crs == "EPSG:32644"


def test_polygon_measurement():
    geometry = Polygon([
        (78.4770, 17.3850),
        (78.4860, 17.3850),
        (78.4860, 17.3940),
        (78.4770, 17.3940),
        (78.4770, 17.3850),
    ])

    result = measure_geometry(
        geometry,
        CRS.from_epsg(4326),
    )

    assert result.status == "MEASURED"
    assert result.measurement_type == "area"
    assert result.unit == "m2"
    assert result.value > 0
    assert result.geodesic_value > 0
    assert result.difference_percent < 0.5
    assert result.projected_crs == "EPSG:32644"


def test_point_has_no_measurement():
    result = measure_geometry(
        Point(78.4770, 17.3850),
        CRS.from_epsg(4326),
    )

    assert result.status == "NO_MEASUREMENT"
    assert result.value is None
    assert result.measurement_type is None


def test_empty_geometry_fails():
    geometry = Polygon()

    result = measure_geometry(
        geometry,
        CRS.from_epsg(4326),
    )

    assert result.status == "ERROR"
    assert result.error_code == "EMPTY_GEOMETRY"


def test_invalid_polygon_is_repaired_before_measurement():
    geometry = Polygon([
        (78.4770, 17.3850),
        (78.4860, 17.3940),
        (78.4860, 17.3850),
        (78.4770, 17.3940),
        (78.4770, 17.3850),
    ])

    result = measure_geometry(
        geometry,
        CRS.from_epsg(4326),
    )

    assert result.status == "MEASURED"
    assert result.measurement_type == "area"
    assert result.value > 0
    assert "GEOMETRY_REPAIRED" in result.warnings
