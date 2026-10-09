
import {
  AlertTriangle,
  CheckCircle2,
  Code2,
  Layers3,
  Map as MapIcon,
  Ruler,
  ShieldCheck,
  Wrench,
} from 'lucide-react'

type QualityReportData = {
  source_crs?: string
  crs_is_geographic?: boolean
  feature_count?: number
  geometry_types?: Record<string, number>
  measurable_features?: number
  no_measurement_features?: number
  unsupported_features?: number
  empty_geometries?: number
  missing_properties?: number
  geometry_repairs?: number
  crs_warnings?: unknown[]
  measurement_warnings?: Array<{
    feature_index?: number
    warnings?: unknown[]
  }>
  measured_features?: number
  measurement_errors?: number
  [key: string]: unknown
}

type Props = {
  report: Record<string, unknown>
}

type ValidationCheck = {
  label: string
  value: number | undefined
}

function displayNumber(value: unknown): string {
  if (typeof value !== 'number' || !Number.isFinite(value)) {
    return 'Not reported'
  }

  return new Intl.NumberFormat('en-US').format(value)
}

function warningText(value: unknown): string {
  if (typeof value !== 'string') {
    return String(value)
  }

  const messages: Record<string, string> = {
    ANTIMERIDIAN_GEODESIC_MEASUREMENT:
      'Geodesic measurement was used for geometry crossing the antimeridian.',
    GEOMETRY_REPAIRED:
      'The geometry was repaired during processing.',
  }

  return messages[value] ?? value
}

export default function QualityReport({ report }: Props) {
  const data = report as QualityReportData

  const warningCounts = new globalThis.Map<string, number>()

  for (const item of data.measurement_warnings ?? []) {
    for (const warning of item.warnings ?? []) {
      const key = String(warning)
      warningCounts.set(key, (warningCounts.get(key) ?? 0) + 1)
    }
  }

  const warningSummary: Array<[string, number]> = Array.from(
    warningCounts.entries(),
  ).sort((a, b) => b[1] - a[1])

  const geometryTypes = Object.entries(data.geometry_types ?? {})

  const hasErrors =
    typeof data.measurement_errors === 'number' &&
    data.measurement_errors > 0

  const totalWarningOccurrences = warningSummary.reduce(
  (total, [, count]) => total + count,
  0,
)

  const validationChecks: ValidationCheck[] = [
    {
      label: 'Features without measurements',
      value: data.no_measurement_features,
    },
    {
      label: 'Unsupported features',
      value: data.unsupported_features,
    },
    {
      label: 'Empty geometries',
      value: data.empty_geometries,
    },
    {
      label: 'Missing properties',
      value: data.missing_properties,
    },
  ]

  return (
    <section className="quality-report">
      <div className="quality-report-heading">
        <div className="quality-report-icon">
          <ShieldCheck size={21} />
        </div>

        <div className="quality-report-title">
          <h3>Data quality report</h3>
          <p>Validation and measurement summary for this dataset.</p>
        </div>

        <span
          className={`quality-status ${
            hasErrors ? 'has-errors' : 'is-healthy'
          }`}
        >
          {hasErrors ? 'Errors detected' : 'Processed'}
        </span>
      </div>

      <div className="quality-metrics">
        <article className="quality-metric">
          <span className="quality-metric-icon">
            <Layers3 size={19} />
          </span>
          <span className="quality-metric-label">Total features</span>
          <strong>{displayNumber(data.feature_count)}</strong>
        </article>

        <article className="quality-metric">
          <span className="quality-metric-icon">
            <CheckCircle2 size={19} />
          </span>
          <span className="quality-metric-label">Measurable features</span>
          <strong>{displayNumber(data.measurable_features)}</strong>
        </article>

        <article className="quality-metric">
          <span className="quality-metric-icon">
            <AlertTriangle size={19} />
          </span>
          <span className="quality-metric-label">Measurement errors</span>
          <strong>{displayNumber(data.measurement_errors)}</strong>
        </article>

        <article className="quality-metric">
          <span className="quality-metric-icon">
            <Wrench size={19} />
          </span>
          <span className="quality-metric-label">Geometry repairs</span>
          <strong>{displayNumber(data.geometry_repairs)}</strong>
        </article>
      </div>

      <div className="quality-section">
        <div className="quality-section-title">
          <MapIcon size={17} />
          <h4>Coordinate reference system</h4>
        </div>

        <div className="quality-info-row">
          <span>Source CRS</span>
          <strong>{data.source_crs ?? 'Not reported'}</strong>
        </div>

        <div className="quality-info-row">
          <span>Coordinate system</span>
          <strong>
            {data.crs_is_geographic == null
              ? 'Not reported'
              : data.crs_is_geographic
                ? 'Geographic'
                : 'Projected'}
          </strong>
        </div>
      </div>

      <div className="quality-section">
        <div className="quality-section-title">
          <Layers3 size={17} />
          <h4>Geometry distribution</h4>
        </div>

        {geometryTypes.length > 0 ? (
          <div className="quality-geometry-list">
            {geometryTypes.map(([type, count]) => {
              const percentage =
                typeof data.feature_count === 'number' &&
                data.feature_count > 0 &&
                Number.isFinite(count)
                  ? Math.min(
                      100,
                      Math.max(0, (count / data.feature_count) * 100),
                    )
                  : 0

              return (
                <div className="quality-geometry-item" key={type}>
                  <div className="quality-geometry-label">
                    <span>{type}</span>
                    <strong>{displayNumber(count)}</strong>
                  </div>

                  <div
                    className="quality-progress-track"
                    role="progressbar"
                    aria-label={`${type} distribution`}
                    aria-valuenow={Math.round(percentage)}
                    aria-valuemin={0}
                    aria-valuemax={100}
                  >
                    <div
                      className="quality-progress-fill"
                      style={{ width: `${percentage}%` }}
                    />
                  </div>
                </div>
              )
            })}
          </div>
        ) : (
          <p className="quality-muted">
            No geometry distribution was reported.
          </p>
        )}
      </div>

      <div className="quality-section">
        <div className="quality-section-title">
          <Ruler size={17} />
          <h4>Validation checks</h4>
        </div>

        {validationChecks.map(({ label, value }) => (
          <div className="quality-info-row" key={label}>
            <span>{label}</span>
            <strong>{displayNumber(value)}</strong>
          </div>
        ))}
      </div>

      {(warningSummary.length > 0 ||
        (data.crs_warnings?.length ?? 0) > 0) && (
        <div className="quality-section">
          <div className="quality-section-title">
            <AlertTriangle size={17} />
            <h4>Warnings and processing notes</h4>
            <span className="quality-warning-count">
  {totalWarningOccurrences +
    (data.crs_warnings?.length ?? 0)}
</span>
          </div>

          {data.crs_warnings?.map((warning, index) => (
            <div className="quality-warning-item" key={`crs-${index}`}>
              <AlertTriangle size={16} />
              <span>{warningText(warning)}</span>
            </div>
          ))}

          {warningSummary.map(([warning, count]) => (
            <div className="quality-warning-item" key={warning}>
              <AlertTriangle size={16} />
              <div>
                <span>{warningText(warning)}</span>
                <small>
                  Affects {count} feature{count === 1 ? '' : 's'}
                </small>
              </div>
            </div>
          ))}
        </div>
      )}

      <details className="quality-raw-details">
        <summary>
          <Code2 size={16} />
          View advanced JSON details
        </summary>

        <pre>{JSON.stringify(report, null, 2)}</pre>
      </details>
    </section>
  )
}
