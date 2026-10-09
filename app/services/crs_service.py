from dataclasses import dataclass, field

import geopandas as gpd
from pyproj import CRS
from shapely.geometry.base import BaseGeometry


@dataclass
class CRSSelection:
    source_crs: str
    projected_crs: str
    method: str
    warnings: list[str] = field(default_factory=list)


def crs_label(crs: CRS) -> str:
    authority = crs.to_authority(min_confidence=70)
    if authority:
        return f"{authority[0]}:{authority[1]}"
    return crs.name


def select_projected_crs(
    geometry: BaseGeometry,
    source_crs: CRS,
) -> CRSSelection:
    if source_crs is None:
        raise ValueError("Source CRS is required.")

    source_label = crs_label(source_crs)

    if not source_crs.is_geographic:
        return CRSSelection(
            source_crs=source_label,
            projected_crs=source_label,
            method="source_projected_crs",
        )

    geometry_wgs84 = gpd.GeoSeries(
        [geometry],
        crs=source_crs,
    ).to_crs("EPSG:4326").iloc[0]

    centroid = geometry_wgs84.centroid
    longitude = centroid.x
    latitude = centroid.y

    if not (-180 <= longitude <= 180 and -90 <= latitude <= 90):
        raise ValueError("Geometry is outside valid WGS84 bounds.")

    zone = int((longitude + 180) // 6) + 1

    if latitude >= 0:
        epsg = 32600 + zone
    else:
        epsg = 32700 + zone

    warnings = []

    min_x, _, max_x, _ = geometry_wgs84.bounds
    longitude_span = max_x - min_x

    if longitude_span > 6:
        warnings.append(
            "Geometry spans more than one UTM zone; measurement may have reduced accuracy."
        )

    projected = CRS.from_epsg(epsg)

    return CRSSelection(
        source_crs=source_label,
        projected_crs=crs_label(projected),
        method="utm_from_centroid",
        warnings=warnings,
    )