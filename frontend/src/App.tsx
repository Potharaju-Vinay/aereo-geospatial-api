
import GeoMap from './GeoMap'
import QualityReport from './QualityReport'
import { useEffect, useRef, useState } from 'react'
import {
  Activity,
  AlertCircle,
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  FileArchive,
  FileCode2,
  FileUp,
  Layers3,
  LoaderCircle,
  Map,
  RefreshCw,
  Ruler,
  Search,
  ShieldCheck,
  UploadCloud,
  X,
} from 'lucide-react'
import './App.css'

const API = 'http://127.0.0.1:8000'

type GeoFile = {
  id: string
  filename: string
  file_type: string
  feature_count: number
  crs: string | null
  status: string
  quality_report?: Record<string, unknown> | null
  error_code?: string | null
  error_message?: string | null
  created_at: string
  completed_at?: string | null
}

type Feature = {
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

type Page = {
  items: Feature[]
  page: number
  page_size: number
  total: number
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API}${path}`, init)
  const data = await response.json().catch(() => null)

  if (!response.ok) {
    throw new Error(
      data?.detail || data?.error_message || `Request failed (${response.status})`,
    )
  }

  return data as T
}

function formatNumber(value: number | null | undefined) {
  if (value == null || !Number.isFinite(value)) return '—'

  return new Intl.NumberFormat('en-US', {
    maximumFractionDigits: 3,
  }).format(value)
}

function formatDate(value?: string | null) {
  if (!value) return '—'

  const date = new Date(value)

  return Number.isNaN(date.getTime()) ? value : date.toLocaleString()
}

function App() {
  const [healthy, setHealthy] = useState<boolean | null>(null)
  const [file, setFile] = useState<GeoFile | null>(null)
  const [page, setPage] = useState<Page | null>(null)
  const [pageNumber, setPageNumber] = useState(1)
  const [geometryFilter, setGeometryFilter] = useState('')
  const [search, setSearch] = useState('')
  const [selected, setSelected] = useState<Feature | null>(null)
  const [busy, setBusy] = useState(false)
  const [dragging, setDragging] = useState(false)
  const [error, setError] = useState('')
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    request<{ status: string }>('/health')
      .then(() => setHealthy(true))
      .catch(() => setHealthy(false))
  }, [])

  async function loadFile(
    fileId: string,
    nextPage = 1,
    filter = geometryFilter,
  ) {
    const details = await request<GeoFile>(`/api/files/${fileId}/`)
    setFile(details)

    const params = new URLSearchParams({
      page: String(nextPage),
      page_size: '20',
    })

    if (filter) {
      params.set('geometry_type', filter)
    }

    const measurements = await request<Page>(
      `/api/files/${fileId}/measurements/?${params.toString()}`,
    )

    setPage(measurements)
    setPageNumber(nextPage)
    setSelected(null)
  }

  async function uploadFile(upload: File) {
    const name = upload.name.toLowerCase()

    if (!name.endsWith('.kml') && !name.endsWith('.zip')) {
      setError('Choose a .kml file or a zipped Shapefile (.zip).')
      return
    }

    setBusy(true)
    setError('')
    setFile(null)
    setPage(null)
    setSelected(null)

    try {
      const body = new FormData()
      body.append('file', upload)

      const uploaded = await request<GeoFile>('/api/files/', {
        method: 'POST',
        body,
      })

      await loadFile(uploaded.id, 1, '')
      setGeometryFilter('')
      setSearch('')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Upload failed.')
    } finally {
      setBusy(false)
    }
  }

  async function changePage(next: number, filter = geometryFilter) {
    if (!file || next < 1) return

    setBusy(true)
    setError('')

    try {
      await loadFile(file.id, next, filter)
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : 'Could not load measurements.',
      )
    } finally {
      setBusy(false)
    }
  }

  async function changeFilter(filter: string) {
    setGeometryFilter(filter)
    await changePage(1, filter)
  }

  const visibleItems = (page?.items ?? []).filter((item) => {
    const query = search.trim().toLowerCase()

    if (!query) return true

    return (
      item.geometry_type.toLowerCase().includes(query) ||
      String(item.feature_index).includes(query) ||
      JSON.stringify(item.properties).toLowerCase().includes(query)
    )
  })

  const measuredOnPage = (page?.items ?? []).filter(
    (item) =>
      item.measurement_value != null && item.status === 'MEASURED',
  ).length

  const warningCount = (page?.items ?? []).filter(
    (item) => item.warnings?.length > 0,
  ).length

  const mappedCount = (page?.items ?? []).filter(
    (item) => item.geometry != null,
  ).length

  const totalPages = Math.max(
    1,
    Math.ceil((page?.total ?? 0) / 20),
  )

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <a
          className="brand"
          href="#"
          aria-label="GeoMeasure home"
          onClick={(event) => {
            event.preventDefault()
            window.scrollTo({ top: 0, behavior: 'smooth' })
          }}
        >
          <span className="brand-mark">
            <Map size={23} />
          </span>
          <span>
            <strong>GeoMeasure</strong>
            <small>SPATIAL INTELLIGENCE</small>
          </span>
        </a>

        <div className="nav-caption">WORKSPACE</div>

        <button
          className="nav-item active"
          onClick={() =>
            window.scrollTo({ top: 0, behavior: 'smooth' })
          }
        >
          <Layers3 size={18} /> Overview
        </button>

        <button
          className="nav-item"
          onClick={() => inputRef.current?.click()}
        >
          <FileUp size={18} /> Upload data
        </button>

        <button
          className="nav-item"
          onClick={() =>
            document
              .getElementById('features')
              ?.scrollIntoView({ behavior: 'smooth' })
          }
        >
          <Ruler size={18} /> Measurements
        </button>

        <div className="sidebar-bottom">
          <div className="security-card">
            <ShieldCheck size={20} />
            <strong>CRS-aware analysis</strong>
            <p>
              Measurements calculated by your geospatial processing API.
            </p>
          </div>

          <div className="api-status">
            <span
              className={`status-dot ${
                healthy ? 'online' : healthy === false ? 'offline' : ''
              }`}
            />
            <span>Backend API</span>
            <strong>
              {healthy === null
                ? 'Checking'
                : healthy
                  ? 'Connected'
                  : 'Offline'}
            </strong>
          </div>
        </div>
      </aside>

      <main className="main-content">
        <header className="topbar">
          <div>
            <div className="breadcrumb">
              Workspace <span>/</span> Overview
            </div>
            <h1>Geospatial workspace</h1>
          </div>

          <div className="topbar-actions">
            <span
              className={`connection-pill ${healthy ? 'connected' : ''}`}
            >
              <Activity size={15} />
              {healthy === null
                ? 'Connecting'
                : healthy
                  ? 'API connected'
                  : 'API unavailable'}
            </span>

            <button
              className="primary-button"
              onClick={() => inputRef.current?.click()}
            >
              <FileUp size={17} /> Upload file
            </button>
          </div>
        </header>

        <section className="welcome-row">
          <div>
            <p className="eyebrow">GEOSPATIAL DATA ANALYSIS</p>
            <h2>
              Turn geographic data into
              <br className="desktop-break" /> meaningful measurements.
            </h2>
            <p className="welcome-copy">
              Upload a KML or zipped Shapefile to inspect features,
              calculate area and length, and review measurement quality.
            </p>
          </div>

          <div className="welcome-icon">
            <Map size={64} strokeWidth={1.1} />
          </div>
        </section>

        {error && (
          <div className="alert error-alert" role="alert">
            <AlertCircle size={19} />
            <span>{error}</span>
            <button
              aria-label="Dismiss error"
              onClick={() => setError('')}
            >
              <X size={17} />
            </button>
          </div>
        )}

        <section className="upload-card">
          <div className="section-heading">
            <div className="section-icon">
              <UploadCloud size={20} />
            </div>
            <div>
              <h3>Import geospatial data</h3>
              <p>Start by uploading a supported file</p>
            </div>
          </div>

          <button
            className={`dropzone ${dragging ? 'dragging' : ''}`}
            onClick={() => inputRef.current?.click()}
            onDragOver={(event) => {
              event.preventDefault()
              setDragging(true)
            }}
            onDragLeave={() => setDragging(false)}
            onDrop={(event) => {
              event.preventDefault()
              setDragging(false)

              const dropped = event.dataTransfer.files[0]

              if (dropped) void uploadFile(dropped)
            }}
            disabled={busy}
          >
            <span className="upload-icon">
              <UploadCloud size={27} />
            </span>

            <strong>
              {busy
                ? 'Processing your file…'
                : 'Drag and drop your file here'}
            </strong>

            <span className="drop-description">
              or click to browse from your computer
            </span>

            <span className="supported-files">
              <span>
                <FileArchive size={15} /> Shapefile ZIP
              </span>
              <span>
                <FileCode2 size={15} /> KML
              </span>
            </span>

            {busy && <LoaderCircle className="spinner" size={20} />}
          </button>

          <input
            ref={inputRef}
            className="hidden-input"
            type="file"
            accept=".zip,.kml,application/zip,application/vnd.google-earth.kml+xml"
            onChange={(event) => {
              const selectedFile = event.target.files?.[0]

              if (selectedFile) void uploadFile(selectedFile)

              event.target.value = ''
            }}
          />

          <p className="privacy-note">
            <ShieldCheck size={14} /> Files are processed by your configured
            GeoMeasure API.
          </p>
        </section>

        {file && page && (
          <>
            <section className="stats-grid">
              <StatCard
                icon={<Layers3 size={20} />}
                label="Total features"
                value={formatNumber(file.feature_count)}
                detail="From uploaded dataset"
              />

              <StatCard
                icon={<Ruler size={20} />}
                label="Measured on this page"
                value={formatNumber(measuredOnPage)}
                detail="Current page only"
              />

              <StatCard
                icon={<AlertCircle size={20} />}
                label="Warnings on this page"
                value={formatNumber(warningCount)}
                detail="Review measurement notes"
              />

              <StatCard
                icon={<CheckCircle2 size={20} />}
                label="Processing status"
                value={file.status}
                detail={file.crs || 'Source CRS not reported'}
                compact
              />
            </section>

            <section className="dataset-card">
              <div className="dataset-heading">
                <div className="file-badge">
                  <FileCode2 size={22} />
                </div>

                <div className="dataset-name">
                  <h3>{file.filename}</h3>
                  <p>
                    {file.file_type} <span>•</span> Uploaded{' '}
                    {formatDate(file.created_at)}
                  </p>
                </div>

                <button
                  className="icon-button"
                  title="Refresh results"
                  disabled={busy}
                  onClick={() => void changePage(1)}
                >
                  <RefreshCw size={17} />
                </button>
              </div>

              <div className="metadata-grid">
                <Metadata label="File ID" value={file.id} />
                <Metadata
                  label="Source CRS"
                  value={file.crs || 'Not reported'}
                />
                <Metadata
                  label="Features"
                  value={String(file.feature_count)}
                />
                <Metadata
                  label="Completed"
                  value={formatDate(file.completed_at)}
                />
              </div>

              {file.error_message && (
                <div className="alert error-alert">
                  <AlertCircle size={18} />
                  {file.error_message}
                </div>
              )}

              {file.quality_report && (
  <QualityReport report={file.quality_report} />
)}
            </section>

            <section className="features-card map-section">
              <div className="features-heading">
                <div>
                  <h3>Geospatial map</h3>
                  <p>
                    Explore uploaded geometries. Select a feature to view
                    its details below.
                  </p>
                </div>

                <span className="result-count">
                  {formatNumber(mappedCount)} geometries
                </span>
              </div>

              <GeoMap
                items={page.items}
                selectedId={selected?.id ?? null}
                onSelect={(feature) => setSelected(feature)}
              />
            </section>

            <section className="features-card" id="features">
              <div className="features-heading">
                <div>
                  <h3>Feature measurements</h3>
                  <p>Real results returned by the GeoMeasure API</p>
                </div>

                <span className="result-count">
                  {formatNumber(page.total)} features
                </span>
              </div>

              <div className="table-controls">
                <label className="search-box">
                  <Search size={17} />
                  <input
                    value={search}
                    onChange={(event) => setSearch(event.target.value)}
                    placeholder="Search features or properties…"
                  />
                </label>

                <select
                  value={geometryFilter}
                  onChange={(event) =>
                    void changeFilter(event.target.value)
                  }
                  aria-label="Filter by geometry type"
                  disabled={busy}
                >
                  <option value="">All geometry types</option>
                  <option value="Point">Point</option>
                  <option value="MultiPoint">MultiPoint</option>
                  <option value="LineString">LineString</option>
                  <option value="MultiLineString">MultiLineString</option>
                  <option value="Polygon">Polygon</option>
                  <option value="MultiPolygon">MultiPolygon</option>
                </select>
              </div>

              <div className="table-wrap">
                <table>
                  <thead>
                    <tr>
                      <th>Feature</th>
                      <th>Geometry type</th>
                      <th>Measurement</th>
                      <th>Unit</th>
                      <th>Status</th>
                      <th />
                    </tr>
                  </thead>

                  <tbody>
                    {visibleItems.map((item) => (
                      <tr
                        key={item.id}
                        onClick={() => setSelected(item)}
                        className={
                          selected?.id === item.id ? 'selected-row' : ''
                        }
                      >
                        <td>
                          <strong>#{item.feature_index}</strong>
                          <small>ID {item.id}</small>
                        </td>

                        <td>
                          <span className="geometry-tag">
                            {item.geometry_type}
                          </span>
                        </td>

                        <td className="measurement-cell">
                          {formatNumber(item.measurement_value)}
                        </td>

                        <td>{item.measurement_unit || '—'}</td>

                        <td>
                          <StatusPill status={item.status} />
                        </td>

                        <td>
                          <button
                            className="row-action"
                            aria-label={`View feature ${item.feature_index}`}
                            onClick={(event) => {
                              event.stopPropagation()
                              setSelected(item)
                            }}
                          >
                            <ChevronRight size={17} />
                          </button>
                        </td>
                      </tr>
                    ))}

                    {visibleItems.length === 0 && (
                      <tr>
                        <td colSpan={6} className="empty-cell">
                          {busy
                            ? 'Loading measurements…'
                            : 'No features match your search.'}
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>

              <div className="pagination">
                <span>
                  Page {page.page} of {totalPages}
                </span>

                <div>
                  <button
                    className="page-button"
                    aria-label="Previous page"
                    disabled={busy || pageNumber <= 1}
                    onClick={() => void changePage(pageNumber - 1)}
                  >
                    <ChevronLeft size={17} /> Previous
                  </button>

                  <button
                    className="page-button"
                    disabled={busy || pageNumber >= totalPages}
                    onClick={() => void changePage(pageNumber + 1)}
                  >
                    Next <ChevronRight size={17} />
                  </button>
                </div>
              </div>
            </section>

            {selected && (
              <section className="detail-card" id="feature-details">
                <div className="features-heading">
                  <div>
                    <h3>Feature #{selected.feature_index}</h3>
                    <p>Detailed measurement and properties</p>
                  </div>

                  <button
                    className="icon-button"
                    aria-label="Close feature details"
                    onClick={() => setSelected(null)}
                  >
                    <X size={18} />
                  </button>
                </div>

                <div className="detail-grid">
                  <Metadata
                    label="Geometry"
                    value={selected.geometry_type}
                  />

                  <Metadata
                    label="Measurement type"
                    value={selected.measurement_type || 'Not applicable'}
                  />

                  <Metadata
                    label="Measurement value"
                    value={
                      selected.measurement_value == null
                        ? 'Not available'
                        : `${formatNumber(selected.measurement_value)} ${selected.measurement_unit || ''}`
                    }
                  />

                  <Metadata
                    label="Feature status"
                    value={selected.status}
                  />
                </div>

                {selected.warnings.length > 0 && (
                  <div className="warning-box">
                    <AlertCircle size={18} />
                    <div>
                      <strong>Measurement warnings</strong>
                      <ul>
                        {selected.warnings.map((warning, index) => (
                          <li key={index}>
                            {typeof warning === 'string'
                              ? warning
                              : JSON.stringify(warning)}
                          </li>
                        ))}
                      </ul>
                    </div>
                  </div>
                )}

                {selected.error_message && (
                  <div className="alert error-alert">
                    <AlertCircle size={18} />
                    {selected.error_message}
                  </div>
                )}

                <h4 className="subheading">Feature properties</h4>
                <pre className="json-view">
                  {JSON.stringify(selected.properties, null, 2)}
                </pre>

                <h4 className="subheading">Measurement provenance</h4>

                {selected.provenance ? (
                  <>
                    <div className="detail-grid">
                      <Metadata
                        label="Projected CRS"
                        value={String(
                          selected.provenance.projected_crs ??
                            'Not available',
                        )}
                      />

                      <Metadata
                        label="Geodesic reference"
                        value={
                          selected.provenance.geodesic_value == null
                            ? 'Not available'
                            : `${formatNumber(Number(selected.provenance.geodesic_value))} ${selected.measurement_unit ?? ''}`
                        }
                      />

                      <Metadata
                        label="Difference percentage"
                        value={
                          selected.provenance.difference_percent == null
                            ? 'Not available'
                            : `${formatNumber(Number(selected.provenance.difference_percent))}%`
                        }
                      />

                      <Metadata
                        label="Measurement method"
                        value={String(
                          selected.provenance.method ?? 'Not reported',
                        )}
                      />
                    </div>

                    <details className="quality-details">
                      <summary>View complete provenance data</summary>
                      <pre className="json-view">
                        {JSON.stringify(selected.provenance, null, 2)}
                      </pre>
                    </details>
                  </>
                ) : (
                  <p className="welcome-copy">
                    Provenance details are not available for this
                    measurement.
                  </p>
                )}

                <h4 className="subheading">Geometry GeoJSON</h4>
                <pre className="json-view">
                  {JSON.stringify(selected.geometry, null, 2)}
                </pre>
              </section>
            )}
          </>
        )}

        {!file && (
          <section className="empty-workspace">
            <div className="empty-illustration">
              <Layers3 size={30} />
            </div>
            <h3>Your workspace is ready</h3>
            <p>
              Upload a dataset to see its actual features, measurements,
              and data quality details here.
            </p>
          </section>
        )}

        <footer className="footer">
          <span>GeoMeasure · Geospatial Analysis</span>
          <span>
            <span
              className={`status-dot ${healthy ? 'online' : ''}`}
            />{' '}
            Powered by your FastAPI backend
          </span>
        </footer>
      </main>
    </div>
  )
}

function StatCard({
  icon,
  label,
  value,
  detail,
  compact = false,
}: {
  icon: React.ReactNode
  label: string
  value: string
  detail: string
  compact?: boolean
}) {
  return (
    <div className="stat-card">
      <div className="stat-top">
        <span className="stat-icon">{icon}</span>
        <span>{label}</span>
      </div>
      <strong
        className={compact ? 'stat-value compact-value' : 'stat-value'}
      >
        {value}
      </strong>
      <p>{detail}</p>
    </div>
  )
}

function Metadata({
  label,
  value,
}: {
  label: string
  value: string
}) {
  return (
    <div className="metadata-item">
      <span>{label}</span>
      <strong title={value}>{value}</strong>
    </div>
  )
}

function StatusPill({ status }: { status: string }) {
  const normalized = status.toUpperCase()
  const success = ['MEASURED', 'COMPLETED', 'SUCCESS'].includes(normalized)
  const failed = ['FAILED', 'ERROR', 'REJECTED'].includes(normalized)

  return (
    <span
      className={`status-pill ${success ? 'success' : failed ? 'failed' : ''}`}
    >
      <span />
      {status}
    </span>
  )
}

export default App
