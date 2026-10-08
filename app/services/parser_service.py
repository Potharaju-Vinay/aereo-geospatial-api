"""Reads KML / Shapefile into a uniform list of features.

Whatever the input format, the rest of the system sees the same shape:
a source CRS plus a list of ParsedFeature(index, geometry, properties).
"""
import datetime as dt
import logging
import math
from dataclasses import dataclass, field
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import pyogrio
from pyproj import CRS
from shapely.geometry.base import BaseGeometry

from app.core.exceptions import AppError, ErrorCode

logger = logging.getLogger(__name__)

EMPTY_TYPE = "Empty"

# Rendering-only fields that GDAL attaches to every KML placemark. They are
# not survey data, so they are left out of the feature properties.
KML_RENDERING_FIELDS = {
    "tessellate", "extrude", "visibility", "drawOrder", "icon",
    "altitudeMode", "timestamp", "begin", "end", "snippet",
}


@dataclass
class ParsedFeature:
    index: int
    geometry: BaseGeometry | None
    properties: dict

    @property
    def geometry_type(self) -> str:
        if self.geometry is None or self.geometry.is_empty:
            return EMPTY_TYPE
        return self.geometry.geom_type


@dataclass
class ParsedFile:
    file_type: str
    source_crs: CRS
    features: list[ParsedFeature] = field(default_factory=list)

    @property
    def crs_label(self) -> str:
        return crs_label(self.source_crs)


def crs_label(crs: CRS) -> str:
    """'EPSG:4326' when the CRS has an authority code, else its name."""
    authority = crs.to_authority(min_confidence=70)
    if authority:
        return f"{authority[0]}:{authority[1]}"
    return crs.name


def _json_safe(value):
    """Make a pandas/numpy value storable in a JSON column."""
    if value is None or value is pd.NaT:
        return None
    if isinstance(value, np.datetime64):
        return None if np.isnat(value) else pd.Timestamp(value).isoformat()
    if isinstance(value, np.generic):
        value = value.item()
    if isinstance(value, float) and math.isnan(value):
        return None
    if isinstance(value, (dt.datetime, dt.date, pd.Timestamp)):
        return value.isoformat()
    if isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


def _frame_to_features(
    gdf: gpd.GeoDataFrame, drop_nulls: bool, ignore: set[str] = frozenset()
) -> list[ParsedFeature]:
    prop_columns = [c for c in gdf.columns if c != gdf.geometry.name and c not in ignore]
    features = []
    for i, (_, row) in enumerate(gdf.iterrows()):
        props = {col: _json_safe(row[col]) for col in prop_columns}
        if drop_nulls:
            props = {k: v for k, v in props.items() if v is not None}
        geom = row[gdf.geometry.name]
        features.append(ParsedFeature(index=i, geometry=geom if geom is not None else None, properties=props))
    return features


def parse_kml(path: Path) -> ParsedFile:
    """KML can hold several layers (one per Folder), so read them all.

    KML coordinates are always WGS84 longitude/latitude (EPSG:4326).
    """
    try:
        layers = [name for name, _ in pyogrio.list_layers(path)]
        frames = []
        for layer in layers:
            frame = pyogrio.read_dataframe(path, layer=layer)
            if len(frame):
                frames.append(frame)
    except Exception as exc:
        logger.warning("kml_parse_failed path=%s error=%s", path.name, exc)
        raise AppError(422, ErrorCode.INVALID_FILE_CONTENT, f"Could not read KML: {exc}")

    if not frames:
        raise AppError(422, ErrorCode.NO_FEATURES, "The KML file contains no features.")

    gdf = pd.concat(frames, ignore_index=True)
    gdf = gpd.GeoDataFrame(gdf, geometry=frames[0].geometry.name, crs=frames[0].crs)
    crs = gdf.crs or CRS.from_epsg(4326)
    return ParsedFile("kml", crs, _frame_to_features(gdf, True, KML_RENDERING_FIELDS))


def parse_shapefile(shp_path: Path) -> ParsedFile:
    try:
        gdf = pyogrio.read_dataframe(shp_path)
    except Exception as exc:
        logger.warning("shapefile_parse_failed path=%s error=%s", shp_path.name, exc)
        raise AppError(422, ErrorCode.INVALID_FILE_CONTENT, f"Could not read Shapefile: {exc}")

    if gdf.crs is None:
        raise AppError(
            422,
            ErrorCode.MISSING_CRS,
            "The Shapefile has no coordinate reference system (.prj missing or unreadable). "
            "Measurements cannot be calculated safely without it.",
        )
    if len(gdf) == 0:
        raise AppError(422, ErrorCode.NO_FEATURES, "The Shapefile contains no features.")

    return ParsedFile("shapefile", CRS.from_user_input(gdf.crs), _frame_to_features(gdf, drop_nulls=False))
