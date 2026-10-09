
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
    return crs.to_string()


def select_projected_crs(
    geometry: BaseGeometry,
    source_crs: CRS,
) -> CRSSelection:
    if source_crs is None:
        raise ValueError("Source CRS is required.")

    source_crs = CRS.from_user_input(source_crs)
    source_label = crs_label(source_crs)

    if geometry is None or geometry.is_empty:
        raise ValueError("A non-empty geometry is required for CRS selection.")

    geometry_wgs84 = gpd.GeoSeries(
        [geometry],
        crs=source_crs,
    ).to_crs("EPSG:4326").iloc[0]

    min_x, min_y, max_x, max_y = geometry_wgs84.bounds

    if min_x < -180 or max_x > 180 or min_y < -90 or max_y > 90:
        raise ValueError("Geometry is outside valid WGS84 coordinate bounds.")

    longitude_span = max_x - min_x
    latitude_span = max_y - min_y

    if longitude_span > 180:
        raise ValueError(
            "Geometry may cross the antimeridian; split or normalize it "
            "before measurement."
        )

    centroid = geometry_wgs84.centroid
    longitude = centroid.x
    latitude = centroid.y

    if not (-180 <= longitude <= 180 and -90 <= latitude <= 90):
        raise ValueError("Geometry centroid is outside valid WGS84 bounds.")

    warnings = []

    if source_crs.is_projected:
        axes = source_crs.axis_info
        uses_metres = (
            len(axes) >= 2
            and all(
                axis.unit_name.lower() in {"metre", "meter"}
                for axis in axes[:2]
            )
        )

        if uses_metres and longitude_span <= 6 and latitude_span <= 8:
            return CRSSelection(
                source_crs=source_label,
                projected_crs=source_label,
                method="source_projected_crs",
            )

        if not uses_metres:
            warnings.append(
                "Source CRS is projected but does not use metres; "
                "a metric CRS was selected for measurement."
            )

    
    if latitude_span > 8 or longitude_span > 6:
        is_polygon = geometry_wgs84.geom_type in {
            "Polygon",
            "MultiPolygon",
        }

        if is_polygon:
            if not -86 <= latitude <= 86:
                raise ValueError(
                    "Large polygon is outside the supported latitude range "
                    "for the selected equal-area projection."
                )

            warnings.append(
                "Large polygon: using a global equal-area projection."
            )

            return CRSSelection(
                source_crs=source_label,
                projected_crs="EPSG:6933",
                method="global_equal_area",
                warnings=warnings,
            )

        if not -80 <= latitude <= 84:
            raise ValueError(
                "Large line is outside the standard UTM latitude range."
            )

        zone = min(60, max(1, int((longitude + 180) // 6) + 1))
        epsg = (32600 if latitude >= 0 else 32700) + zone

        warnings.append(
            "Large line: using centroid-based UTM; verify length accuracy "
            "for the full extent."
        )

        return CRSSelection(
            source_crs=source_label,
            projected_crs=crs_label(CRS.from_epsg(epsg)),
            method="utm_from_centroid",
            warnings=warnings,
        )


    if not -80 <= latitude <= 84:
        raise ValueError(
            "The geometry is outside the standard UTM latitude range "
            "(-80 to 84 degrees). A suitable polar or regional projection "
            "is required."
        )

    zone = min(60, max(1, int((longitude + 180) // 6) + 1))
    epsg = (32600 if latitude >= 0 else 32700) + zone
    projected = CRS.from_epsg(epsg)

    return CRSSelection(
        source_crs=source_label,
        projected_crs=crs_label(projected),
        method="utm_from_centroid",
        warnings=warnings,
    )
