"""Data quality report for an uploaded file.

Built right after parsing so the client can see, at a glance, how clean the
data was. Friday's measurement step adds repair / measurement warnings.
"""
from collections import Counter

from app.services.parser_service import EMPTY_TYPE, ParsedFile

SUPPORTED_MEASURED = {"Polygon", "MultiPolygon", "LineString", "MultiLineString"}
NO_MEASUREMENT = {"Point", "MultiPoint"}


def build_ingest_report(parsed: ParsedFile) -> dict:
    types = Counter(f.geometry_type for f in parsed.features)
    missing_props = sum(
        1 for f in parsed.features if all(v is None for v in f.properties.values())
    )
    measurable = sum(n for t, n in types.items() if t in SUPPORTED_MEASURED)
    points = sum(n for t, n in types.items() if t in NO_MEASUREMENT)
    empty = types.get(EMPTY_TYPE, 0)
    unsupported = len(parsed.features) - measurable - points - empty

    return {
        "source_crs": parsed.crs_label,
        "crs_is_geographic": bool(parsed.source_crs.is_geographic),
        "feature_count": len(parsed.features),
        "geometry_types": dict(types),
        "measurable_features": measurable,
        "no_measurement_features": points,
        "unsupported_features": unsupported,
        "empty_geometries": empty,
        "missing_properties": missing_props,
        "geometry_repairs": 0,
        "crs_warnings": [],
        "measurement_warnings": [],
    }
