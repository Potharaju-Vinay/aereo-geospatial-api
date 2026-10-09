
import { useEffect, useMemo } from 'react'
import { MapContainer, TileLayer, GeoJSON, useMap } from 'react-leaflet'
import L from 'leaflet'
import type {
  Feature as GeoJSONFeature,
  FeatureCollection,
  Geometry,
} from 'geojson'
import 'leaflet/dist/leaflet.css'

type MapFeature = {
  id: number
  feature_index: number
  geometry_type: string
  geometry: Record<string, unknown> | null
  properties: Record<string, unknown>
  measurement_type: string | null
  measurement_value: number | null
  measurement_unit: string | null
  provenance: Record<string, unknown> | null
  warnings: unknown[]
  status: string
  error_code: string | null
  error_message: string | null
}

type Props = {
  items: MapFeature[]
  selectedId: number | null
  onSelect: (feature: MapFeature) => void
}

function FitBounds({ data }: { data: FeatureCollection }) {
  const map = useMap()

  useEffect(() => {
    const layer = L.geoJSON(data)
    const bounds = layer.getBounds()

    if (bounds.isValid()) {
      map.fitBounds(bounds, {
        padding: [24, 24],
        maxZoom: 12,
      })
    }
  }, [data, map])

  return null
}

export default function GeoMap({
  items,
  selectedId,
  onSelect,
}: Props) {
  const data = useMemo<FeatureCollection>(() => ({
    type: 'FeatureCollection',
    features: items
      .filter(
        (item) =>
          item.geometry !== null &&
          typeof item.geometry.type === 'string',
      )
      .map((item): GeoJSONFeature => ({
        type: 'Feature',
        id: item.id,
        geometry: item.geometry as unknown as Geometry,
        properties: {
          ...item.properties,
          feature_index: item.feature_index,
          geometry_type: item.geometry_type,
          measurement_value: item.measurement_value,
          measurement_unit: item.measurement_unit,
          record_id: item.id,
        },
      })),
  }), [items])

  const geoJsonKey = useMemo(
    () => data.features.map((feature) => feature.id).join(','),
    [data],
  )

  return (
    <div className="map-frame">
      {data.features.length === 0 ? (
        <div className="map-empty">
          No geometries are available on this page to display.
        </div>
      ) : (
        <MapContainer
          center={[20, 0]}
          zoom={2}
          scrollWheelZoom
          className="geo-map"
        >
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />

          <FitBounds data={data} />

          <GeoJSON
            key={geoJsonKey}
            data={data}
            style={(feature) => {
              const isSelected =
                Number(feature?.id) === selectedId

              return {
                color: isSelected ? '#e58a32' : '#167d74',
                weight: isSelected ? 3 : 1.5,
                fillColor: isSelected ? '#f5b76c' : '#50c5b1',
                fillOpacity: 0.25,
              }
            }}
            pointToLayer={(_feature, latlng) =>
              L.circleMarker(latlng, {
                radius: 6,
                color: '#167d74',
                fillColor: '#50c5b1',
                fillOpacity: 0.9,
                weight: 2,
              })
            }
            onEachFeature={(feature, layer) => {
              const record = items.find(
                (item) => item.id === Number(feature.id),
              )

              const index =
                record?.feature_index ??
                feature.properties?.feature_index

              const measurement = record?.measurement_value
              const unit = record?.measurement_unit ?? ''

              const formattedMeasurement =
                measurement == null
                  ? 'Not available'
                  : `${new Intl.NumberFormat('en-US', {
                      maximumFractionDigits: 3,
                    }).format(measurement)} ${unit}`

              layer.bindPopup(
                `<strong>Feature #${index}</strong><br/>` +
                  `${String(
                    feature.properties?.geometry_type ?? 'Geometry',
                  )}<br/>` +
                  `Measurement: ${formattedMeasurement}`,
              )

              layer.on('click', () => {
                if (record) {
                  onSelect(record)
                }
              })
            }}
          />
        </MapContainer>
      )}
    </div>
  )
}
