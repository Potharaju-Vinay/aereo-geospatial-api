"""Builds small KML / Shapefile test files with *known* geometry sizes.

Shapes are constructed in UTM zone 44N (EPSG:32644, units = metres) so the
true area/length is exact, then converted to lat/lon when needed. Friday's
measurement tests compare the API's answers against these known values.
"""
import zipfile
from pathlib import Path

import geopandas as gpd
import pyogrio
from pyproj import Transformer
from shapely.geometry import LineString, Point, box

UTM_CRS = "EPSG:32644"
# Roughly Hyderabad, expressed in UTM 44N metres.
_E0, _N0 = Transformer.from_crs("EPSG:4326", UTM_CRS, always_xy=True).transform(78.4867, 17.3850)

KNOWN_AREA_PLOT_A = 1_000_000.0  # 1 km x 1 km
KNOWN_AREA_PLOT_B = 100_000.0  # 500 m x 200 m
KNOWN_LENGTH_ROAD = 1_000.0  # straight 1 km line


def sample_features_utm() -> gpd.GeoDataFrame:
    """Four features in UTM metres: two polygons, one line, one point."""
    return gpd.GeoDataFrame(
        {
            "name": ["Plot A", "Plot B", "Road 1", "Gate"],
            "category": ["parcel", "parcel", "road", "marker"],
        },
        geometry=[
            box(_E0, _N0, _E0 + 1000, _N0 + 1000),
            box(_E0 + 2000, _N0, _E0 + 2500, _N0 + 200),
            LineString([(_E0, _N0 - 500), (_E0 + 1000, _N0 - 500)]),
            Point(_E0 + 500, _N0 + 500),
        ],
        crs=UTM_CRS,
    )


def sample_features_wgs84() -> gpd.GeoDataFrame:
    return sample_features_utm().to_crs("EPSG:4326")


def sample_polygons_wgs84() -> gpd.GeoDataFrame:
    """Polygons only. A Shapefile holds a single geometry type per file."""
    gdf = sample_features_wgs84()
    return gdf[gdf.geom_type == "Polygon"].reset_index(drop=True)


def sample_lines_wgs84() -> gpd.GeoDataFrame:
    gdf = sample_features_wgs84()
    return gdf[gdf.geom_type == "LineString"].reset_index(drop=True)


def write_kml(path: Path, gdf: gpd.GeoDataFrame | None = None) -> Path:
    gdf = sample_features_wgs84() if gdf is None else gdf
    pyogrio.write_dataframe(gdf, path, driver="KML")
    return path


def write_shapefile_zip(
    zip_path: Path,
    gdf: gpd.GeoDataFrame | None = None,
    *,
    include_prj: bool = True,
    include_shx: bool = True,
    include_dbf: bool = True,
) -> Path:
    """Write a shapefile and zip its parts, optionally leaving some out."""
    gdf = sample_polygons_wgs84() if gdf is None else gdf
    work = zip_path.parent / f"_{zip_path.stem}_parts"
    work.mkdir(parents=True, exist_ok=True)
    gdf.to_file(work / "survey.shp", driver="ESRI Shapefile")

    skip = set()
    if not include_prj:
        skip.add(".prj")
    if not include_shx:
        skip.add(".shx")
    if not include_dbf:
        skip.add(".dbf")

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for part in sorted(work.iterdir()):
            if part.suffix.lower() not in skip:
                zf.write(part, part.name)
    return zip_path
