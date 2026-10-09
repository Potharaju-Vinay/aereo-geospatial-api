from dataclasses import dataclass, field

from pyproj import Geod
from shapely.geometry import GeometryCollection, LineString, MultiLineString, MultiPolygon, Polygon
from shapely import make_valid, transform

from app.services.crs_service import select_projected_crs

import logging

logger = logging.getLogger(__name__)


GEOD = Geod(ellps="WGS84")


@dataclass
class MeasurementResult:
    measurement_type: str | None
    value: float | None
    unit: str | None
    projected_crs: str | None
    geodesic_value: float | None
    difference_percent: float | None
    warnings: list[str] = field(default_factory=list)
    status: str = "MEASURED"
    error_code: str | None = None
    error_message: str | None = None


def _geodesic_area(geometry) -> float:
    area, _ = GEOD.geometry_area_perimeter(geometry)
    return abs(area)


def _geodesic_length(geometry) -> float:
    if isinstance(geometry, LineString):
        return _geodesic_line_length(geometry)

    if isinstance(geometry, MultiLineString):
        return sum(_geodesic_line_length(line) for line in geometry.geoms)

    return 0.0


def _geodesic_line_length(line) -> float:
    coordinates = list(line.coords)
    if len(coordinates) < 2:
        return 0.0

    total = 0.0

    for start, end in zip(coordinates, coordinates[1:]):
        _, _, distance = GEOD.inv(
            start[0],
            start[1],
            end[0],
            end[1],
        )
        total += distance

    return total


def _difference_percent(measured: float, reference: float) -> float | None:
    if reference == 0:
        return None

    return abs(measured - reference) / reference * 100



def measure_geometry(geometry, source_crs) -> MeasurementResult:
    if geometry is None or geometry.is_empty:
        return MeasurementResult(
            measurement_type=None,
            value=None,
            unit=None,
            projected_crs=None,
            geodesic_value=None,
            difference_percent=None,
            status="ERROR",
            error_code="EMPTY_GEOMETRY",
            error_message="Geometry is empty.",
        )

    geometry_type = geometry.geom_type

    if geometry_type == "Point":
        return MeasurementResult(
            measurement_type=None,
            value=None,
            unit=None,
            projected_crs=None,
            geodesic_value=None,
            difference_percent=None,
            status="NO_MEASUREMENT",
        )

    if isinstance(geometry, GeometryCollection):
        return MeasurementResult(
            measurement_type=None,
            value=None,
            unit=None,
            projected_crs=None,
            geodesic_value=None,
            difference_percent=None,
            status="UNSUPPORTED",
            error_code="UNSUPPORTED_GEOMETRY",
            error_message="GeometryCollection is not supported.",
        )

    try:
        warnings = []

        if not geometry.is_valid:
            repaired = make_valid(geometry)

            if repaired.is_empty or not repaired.is_valid:
                return MeasurementResult(
                    measurement_type=None,
                    value=None,
                    unit=None,
                    projected_crs=None,
                    geodesic_value=None,
                    difference_percent=None,
                    status="ERROR",
                    error_code="INVALID_GEOMETRY",
                    error_message="Invalid geometry could not be repaired.",
                )

            geometry = repaired
            warnings.append("GEOMETRY_REPAIRED")

        
        from pyproj import CRS, Transformer

        source_crs = CRS.from_user_input(source_crs)
        wgs84_transformer = Transformer.from_crs(
            source_crs,
            "EPSG:4326",
            always_xy=True,
        )

        source_wgs84 = transform(
            geometry,
            wgs84_transformer.transform,
            interleaved=False,
        )

        if isinstance(source_wgs84, (Polygon, MultiPolygon)):
            measurement_type = "area"
            unit = "m2"
            geodesic_value = _geodesic_area(source_wgs84)
        elif isinstance(source_wgs84, (LineString, MultiLineString)):
            measurement_type = "length"
            unit = "m"
            geodesic_value = _geodesic_length(source_wgs84)
        else:
            return MeasurementResult(
                measurement_type=None,
                value=None,
                unit=None,
                projected_crs=None,
                geodesic_value=None,
                difference_percent=None,
                warnings=warnings,
                status="UNSUPPORTED",
                error_code="UNSUPPORTED_GEOMETRY",
                error_message=f"Geometry type '{geometry_type}' is not supported.",
            )

        try:
            selection = select_projected_crs(geometry, source_crs)
            warnings.extend(selection.warnings)

            projected_transformer = Transformer.from_crs(
                source_crs,
                selection.projected_crs,
                always_xy=True,
            )

            projected_geometry = transform(
                geometry,
                projected_transformer.transform,
                interleaved=False,
            )

            value = (
                abs(projected_geometry.area)
                if measurement_type == "area"
                else projected_geometry.length
            )

            difference = _difference_percent(value, geodesic_value)

            if difference is not None and difference > 0.5:
                warnings.append("LARGE_GEODESIC_DIFFERENCE")

            return MeasurementResult(
                measurement_type=measurement_type,
                value=value,
                unit=unit,
                projected_crs=selection.projected_crs,
                geodesic_value=geodesic_value,
                difference_percent=difference,
                warnings=warnings,
            )

        except ValueError as exc:
            if "antimeridian" not in str(exc).lower():
                raise

            warnings.append("ANTIMERIDIAN_GEODESIC_MEASUREMENT")
            return MeasurementResult(
                measurement_type=measurement_type,
                value=geodesic_value,
                unit=unit,
                projected_crs=None,
                geodesic_value=geodesic_value,
                difference_percent=0.0,
                warnings=warnings,
            )

    except Exception:
        logger.exception(
            "Geometry measurement failed: geometry_type=%s, source_crs=%s",
            geometry_type,
            source_crs,
        )
        return MeasurementResult(
            measurement_type=None,
            value=None,
            unit=None,
            projected_crs=None,
            geodesic_value=None,
            difference_percent=None,
            status="ERROR",
            error_code="MEASUREMENT_ERROR",
            error_message="The geometry could not be measured with the supplied CRS.",
        )
