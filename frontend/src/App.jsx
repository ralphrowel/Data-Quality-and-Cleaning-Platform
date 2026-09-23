import { useState, useEffect, useRef } from 'react'
import './App.css'

export default function App() {
  // API Health & Datasets State
  const [apiOnline, setApiOnline] = useState(false)
  const [datasets, setDatasets] = useState([])
  const [selectedDatasetId, setSelectedDatasetId] = useState('')
  const [datasetDetail, setDatasetDetail] = useState(null)
  const [activeVersionId, setActiveVersionId] = useState('')
  const [qualityData, setQualityData] = useState(null)
  const [profileData, setProfileData] = useState(null)

  // UI State
  const [activeTab, setActiveTab] = useState('cleaning') // 'cleaning' or 'issues'
  const [issueFilter, setIssueFilter] = useState('ALL')
  const [isUploading, setIsUploading] = useState(false)
  const [isCleaning, setIsCleaning] = useState(false)
  const [errorMessage, setErrorMessage] = useState('')
  const [successMessage, setSuccessMessage] = useState('')
  const [lastCleaningResult, setLastCleaningResult] = useState(null)

  // Cleaning Form Options
  const [stripWhitespace, setStripWhitespace] = useState(true)
  const [normalizeColumns, setNormalizeColumns] = useState(true)
  const [dropDuplicates, setDropDuplicates] = useState(true)
  const [normalizeDates, setNormalizeDates] = useState(true)

  const fileInputRef = useRef(null)

  // 1. Initial Load: Check API Health & Fetch Datasets
  useEffect(() => {
    checkHealth()
    fetchDatasets()
  }, [])

  // 2. When Selected Dataset Changes, Load Details, Quality & Profile
  useEffect(() => {
    if (selectedDatasetId) {
      loadDataset(selectedDatasetId)
    }
  }, [selectedDatasetId])

  // 3. When Active Version Changes, Refresh Quality & Profile
  useEffect(() => {
    if (selectedDatasetId && activeVersionId) {
      loadQualityReport(selectedDatasetId, activeVersionId)
      loadProfile(selectedDatasetId, activeVersionId)
    }
  }, [activeVersionId])

  async function checkHealth() {
    try {
      const res = await fetch('/api/health/')
      if (res.ok) {
        setApiOnline(true)
      } else {
        setApiOnline(false)
      }
    } catch {
      setApiOnline(false)
    }
  }

  async function fetchDatasets() {
    try {
      const res = await fetch('/api/datasets/')
      if (res.ok) {
        const data = await res.json()
        setDatasets(data.results || [])
        // Auto-select first dataset if none selected
        if (!selectedDatasetId && data.results && data.results.length > 0) {
          setSelectedDatasetId(data.results[0].id)
        }
      }
    } catch (err) {
      console.error('Error fetching datasets:', err)
    }
  }

  async function loadDataset(id) {
    try {
      setErrorMessage('')
      const res = await fetch(`/api/datasets/${id}/`)
      if (res.ok) {
        const data = await res.json()
        setDatasetDetail(data)
        const versions = data.versions || []
        if (versions.length > 0) {
          // Select latest version by default
          const latest = versions[versions.length - 1]
          setActiveVersionId(latest.id)
        }
      } else {
        setErrorMessage('Failed to load dataset details.')
      }
    } catch (err) {
      setErrorMessage(`Error loading dataset: ${err.message}`)
    }
  }

  async function loadQualityReport(datasetId, versionId) {
    try {
      const res = await fetch(`/api/datasets/${datasetId}/quality/?version_id=${versionId}`)
      if (res.ok) {
        const data = await res.json()
        setQualityData(data)
      }
    } catch (err) {
      console.error('Error loading quality report:', err)
    }
  }

  async function loadProfile(datasetId, versionId) {
    try {
      const res = await fetch(`/api/datasets/${datasetId}/profile/?version_id=${versionId}`)
      if (res.ok) {
        const data = await res.json()
        setProfileData(data)
      }
    } catch (err) {
      console.error('Error loading profile:', err)
    }
  }

  // File Upload Handler
  async function handleFileUpload(file) {
    if (!file) return
    if (file.size > 26214400) {
      setErrorMessage('File size exceeds the 25 MB limit.')
      return
    }

    setIsUploading(true)
    setErrorMessage('')
    setSuccessMessage('')

    const formData = new FormData()
    formData.append('file', file)
    formData.append('name', file.name.replace(/\.[^/.]+$/, '').replace(/_/g, ' '))

    try {
      const res = await fetch('/api/datasets/', {
        method: 'POST',
        body: formData,
      })

      if (res.ok) {
        const result = await res.json()
        setSuccessMessage(`Successfully uploaded and profiled "${result.dataset.name}".`)
        await fetchDatasets()
        setSelectedDatasetId(result.dataset.id)
      } else {
        const errData = await res.json()
        setErrorMessage(errData.error || 'Failed to upload dataset.')
      }
    } catch (err) {
      setErrorMessage(`Upload error: ${err.message}`)
    } finally {
      setIsUploading(false)
    }
  }

  // Trigger Cleaning Pipeline
  async function handleRunCleaning() {
    if (!selectedDatasetId) return

    setIsCleaning(true)
    setErrorMessage('')
    setSuccessMessage('')

    const payload = {
      strip_whitespace: stripWhitespace,
      normalize_column_names: normalizeColumns,
      drop_duplicates_subset: dropDuplicates ? null : [],
      date_columns: normalizeDates ? [] : null,
    }

    try {
      const res = await fetch(`/api/datasets/${selectedDatasetId}/clean/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })

      if (res.ok) {
        const result = await res.json()
        setLastCleaningResult(result)
        setSuccessMessage(result.message)
        // Refresh dataset and versions
        await loadDataset(selectedDatasetId)
        await fetchDatasets()
      } else {
        const errData = await res.json()
        setErrorMessage(errData.error || 'Cleaning pipeline failed.')
      }
    } catch (err) {
      setErrorMessage(`Cleaning error: ${err.message}`)
    } finally {
      setIsCleaning(false)
    }
  }

  // Safe CSV Export Handler
  function handleExportCsv() {
    if (!selectedDatasetId) return
    const exportUrl = `/api/datasets/${selectedDatasetId}/export/?version_id=${activeVersionId || ''}`
    window.location.href = exportUrl
  }

  // Helpers for Grade Styles and Circle Gauge
  const report = qualityData?.quality_report
  const overallScore = report ? Number(report.overall_score).toFixed(1) : '0.0'
  const letterGrade = report ? report.grade : 'F'
  const isTrustworthy = Number(overallScore) >= 80.0

  const circumference = 2 * Math.PI * 60
  const strokeOffset = circumference - (Number(overallScore) / 100) * circumference

  const gradeColors = {
    A: '#10b981',
    B: '#38bdf8',
    C: '#f59e0b',
    D: '#f97316',
    F: '#ef4444',
  }
  const activeColor = gradeColors[letterGrade] || '#38bdf8'

  // Issues Filtering
  const issues = qualityData?.issues || []
  const filteredIssues = issues.filter((iss) => {
    if (issueFilter === 'ALL') return true
    return iss.severity?.toUpperCase() === issueFilter
  })

  return (
    <div className="app-container" id="app-root">
      {/* 1. Header Bar */}
      <header className="app-header" id="platform-header">
        <div className="brand-section">
          <div className="brand-icon" id="brand-logo">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
              <path d="m9 12 2 2 4-4"/>
            </svg>
          </div>
          <div>
            <h1 className="brand-title">Data Quality & Cleaning Platform</h1>
            <p className="brand-subtitle">
              Automated Profiling • Deterministic Cleaning • Power BI Governance
            </p>
          </div>
        </div>

        <div className="header-actions">
          <div className="api-status-badge" id="api-status-indicator" title={apiOnline ? 'Django REST API is live' : 'Connecting to API...'}>
            <span className={`status-dot ${apiOnline ? '' : 'offline'}`} />
            <span>{apiOnline ? 'API Online' : 'Connecting...'}</span>
          </div>

          <a
            href="http://127.0.0.1:8000/api/docs/"
            target="_blank"
            rel="noopener noreferrer"
            className="docs-link"
            id="link-swagger-docs"
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
              <polyline points="14 2 14 8 20 8"/>
              <line x1="16" y1="13" x2="8" y2="13"/>
              <line x1="16" y1="17" x2="8" y2="17"/>
              <polyline points="10 9 9 9 8 9"/>
            </svg>
            Swagger API Docs
          </a>
        </div>
      </header>

      {/* Alerts */}
      {errorMessage && (
        <div className="badge badge-critical" style={{ width: '100%', padding: '12px 16px', marginBottom: '20px', borderRadius: '8px' }} id="global-error-banner">
          ⚠️ {errorMessage}
        </div>
      )}
      {successMessage && (
        <div className="badge badge-a" style={{ width: '100%', padding: '12px 16px', marginBottom: '20px', borderRadius: '8px' }} id="global-success-banner">
          ✓ {successMessage}
        </div>
      )}

      {/* 2. Dataset Ingestion & Selection */}
      <section className="dataset-bar" id="dataset-management-section">
        {/* Upload Card */}
        <div className="glass-panel upload-card" id="upload-panel">
          <div className="card-heading">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
              <polyline points="17 8 12 3 7 8"/>
              <line x1="12" y1="3" x2="12" y2="15"/>
            </svg>
            <span>Upload New Dataset</span>
          </div>

          <div
            className="dropzone"
            id="file-dropzone"
            onClick={() => fileInputRef.current?.click()}
            onDragOver={(e) => e.preventDefault()}
            onDrop={(e) => {
              e.preventDefault()
              if (e.dataTransfer.files?.[0]) {
                handleFileUpload(e.dataTransfer.files[0])
              }
            }}
          >
            <input
              type="file"
              ref={fileInputRef}
              className="file-input"
              id="file-input"
              accept=".csv,.xlsx,.xls"
              onChange={(e) => {
                if (e.target.files?.[0]) {
                  handleFileUpload(e.target.files[0])
                }
              }}
            />
            <div className="dropzone-icon">
              {isUploading ? (
                <div className="spinner" style={{ margin: '0 auto', width: '28px', height: '28px' }} />
              ) : (
                <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                  <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                  <path d="M14 2v6h6"/>
                  <path d="M12 18v-6"/>
                  <path d="m9 15 3-3 3 3"/>
                </svg>
              )}
            </div>
            <div className="dropzone-text">
              {isUploading ? 'Uploading and generating quality profile...' : 'Click to browse or drag & drop CSV or Excel'}
            </div>
            <div className="dropzone-sub">Max upload size: 25 MB • Automated Profiling & Parquet Snapshot</div>
          </div>
        </div>

        {/* Existing Datasets Selector */}
        <div className="glass-panel select-card" id="select-panel">
          <div className="card-heading">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <ellipse cx="12" cy="5" rx="9" ry="3"/>
              <path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"/>
              <path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"/>
            </svg>
            <span>Active Dataset Workspace</span>
          </div>

          <label htmlFor="dataset-dropdown" style={{ display: 'block', fontSize: '0.8rem', color: 'var(--text-muted)', marginBottom: '8px' }}>
            SELECT A DATASET TO INSPECT:
          </label>
          <select
            id="dataset-dropdown"
            className="dataset-select-dropdown"
            value={selectedDatasetId}
            onChange={(e) => setSelectedDatasetId(e.target.value)}
          >
            {datasets.map((d) => (
              <option key={d.id} value={d.id}>
                {d.name} ({d.original_filename}) — Grade: {d.latest_grade || 'N/A'} ({d.latest_quality_score ? `${Number(d.latest_quality_score).toFixed(1)}%` : 'Unscored'})
              </option>
            ))}
          </select>

          {datasetDetail && (
            <div style={{ marginTop: '16px', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <div style={{ fontSize: '0.82rem', color: 'var(--text-secondary)' }}>
                <span>Versions: </span>
                <span className="mono" style={{ color: 'var(--text-primary)', fontWeight: 'bold' }}>
                  {datasetDetail.versions?.length || 1}
                </span>
                <span style={{ marginLeft: '12px' }}>Active: </span>
                <select
                  id="version-dropdown"
                  value={activeVersionId}
                  onChange={(e) => setActiveVersionId(e.target.value)}
                  style={{
                    background: 'rgba(255,255,255,0.06)',
                    color: 'var(--cyan-400)',
                    border: '1px solid var(--border-subtle)',
                    borderRadius: '4px',
                    padding: '2px 8px',
                    fontFamily: 'var(--font-mono)',
                    fontSize: '0.8rem'
                  }}
                >
                  {datasetDetail.versions?.map((v) => (
                    <option key={v.id} value={v.id}>
                      v{v.version_number} ({v.row_count?.toLocaleString()} rows)
                    </option>
                  ))}
                </select>
              </div>

              <button
                id="btn-export-csv"
                className="btn btn-secondary"
                style={{ padding: '6px 14px', fontSize: '0.82rem' }}
                onClick={handleExportCsv}
                title="Download safe CSV sanitized against formula injection"
              >
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                  <polyline points="7 10 12 15 17 10"/>
                  <line x1="12" y1="15" x2="12" y2="3"/>
                </svg>
                Export CSV
              </button>
            </div>
          )}
        </div>
      </section>

      {/* 3. Before & After Delta Banner (if cleaning just performed or version > 1) */}
      {lastCleaningResult && (
        <section className="comparison-card animate-fade-in" id="before-after-banner">
          <div className="comparison-header">
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span className="badge badge-a">Pipeline Completed</span>
              <strong style={{ fontSize: '0.95rem', color: '#f8fafc' }}>Transformation Summary</strong>
            </div>
            <span className="score-delta-badge" id="score-delta-indicator">
              Delta: +{lastCleaningResult.score_delta}% Quality Score
            </span>
          </div>

          <div className="comparison-grid">
            <div className="comparison-box">
              <div className="comparison-label">Quality Score</div>
              <div className="comparison-values">
                <span className="val-new">
                  {Number(lastCleaningResult.quality_score?.overall_score || 0).toFixed(1)}%
                </span>
                <span className="badge badge-a" style={{ fontSize: '0.75rem', padding: '2px 8px' }}>
                  {lastCleaningResult.quality_score?.grade}
                </span>
              </div>
            </div>

            <div className="comparison-box">
              <div className="comparison-label">Pipeline Steps Run</div>
              <div className="comparison-values">
                <span className="mono" style={{ color: 'var(--text-primary)' }}>
                  {lastCleaningResult.operations_executed} Transformations
                </span>
              </div>
            </div>

            <div className="comparison-box">
              <div className="comparison-label">Lineage Version</div>
              <div className="comparison-values">
                <span className="mono" style={{ color: 'var(--cyan-400)' }}>
                  v{lastCleaningResult.new_version?.version_number} Created
                </span>
              </div>
            </div>
          </div>
        </section>
      )}

      {/* 4. Scorecard & 4 Dimensions (V8.2) */}
      <section className="scorecard-grid" id="scorecard-section">
        {/* Trust Hero Card */}
        <div className="glass-panel trust-hero-card" id="trust-card">
          <div className="score-circle-wrapper">
            <svg className="score-svg" viewBox="0 0 140 140">
              <circle
                className="score-svg-bg"
                cx="70"
                cy="70"
                r="60"
              />
              <circle
                className="score-svg-progress"
                cx="70"
                cy="70"
                r="60"
                style={{
                  stroke: activeColor,
                  strokeDasharray: circumference,
                  strokeDashoffset: strokeOffset,
                }}
              />
            </svg>
            <div className="score-center-text">
              <div className="score-number" id="overall-score-display">{overallScore}</div>
              <div className="score-percent">/ 100</div>
            </div>
          </div>

          <div className={`badge badge-${letterGrade.toLowerCase()} score-grade-badge`} id="grade-badge">
            Grade {letterGrade}
          </div>

          <div className={`trust-recommendation ${isTrustworthy ? 'trusted' : 'caution'}`} id="trust-status-text">
            {isTrustworthy ? '✓ TRUSTED FOR ANALYSIS' : '⚠ NEEDS CLEANING'}
          </div>

          <p style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
            Calibrated 4-dimension deterministic evaluation
          </p>
        </div>

        {/* Metrics Grid & 4 Dimension Bars */}
        <div className="glass-panel breakdown-panel" id="dimensions-panel">
          {/* Quick Metrics */}
          <div className="metrics-summary-grid">
            <div className="metric-box">
              <div className="metric-label">Total Rows</div>
              <div className="metric-value" id="metric-rows">
                {profileData?.summary?.row_count?.toLocaleString() || report?.row_count?.toLocaleString() || '—'}
              </div>
            </div>

            <div className="metric-box">
              <div className="metric-label">Columns</div>
              <div className="metric-value" id="metric-cols">
                {profileData?.summary?.column_count || '—'}
              </div>
            </div>

            <div className="metric-box">
              <div className="metric-label">Missing Cells</div>
              <div className="metric-value" id="metric-missing" style={{ color: (profileData?.summary?.total_missing_cells || 0) > 0 ? '#fbbf24' : 'var(--text-primary)' }}>
                {profileData?.summary?.total_missing_cells?.toLocaleString() || '0'}
              </div>
            </div>

            <div className="metric-box">
              <div className="metric-label">Duplicate Rows</div>
              <div className="metric-value" id="metric-duplicates" style={{ color: (profileData?.summary?.duplicate_rows || 0) > 0 ? '#f87171' : 'var(--text-primary)' }}>
                {profileData?.summary?.duplicate_rows?.toLocaleString() || '0'}
              </div>
            </div>
          </div>

          {/* 4 Dimensions Breakdown */}
          <div className="dimensions-list">
            {/* Completeness */}
            <div className="dimension-item">
              <div className="dimension-header">
                <span className="dimension-title">
                  <span>Completeness</span>
                  <span className="dimension-weight">(Weight: 30%)</span>
                </span>
                <span className="dimension-score" style={{ color: '#38bdf8' }}>
                  {report ? `${Number(report.completeness_score).toFixed(1)}%` : '—'}
                </span>
              </div>
              <div className="progress-track">
                <div
                  className="progress-fill fill-completeness"
                  style={{ width: `${report ? report.completeness_score : 0}%` }}
                />
              </div>
            </div>

            {/* Validity */}
            <div className="dimension-item">
              <div className="dimension-header">
                <span className="dimension-title">
                  <span>Validity</span>
                  <span className="dimension-weight">(Weight: 30%)</span>
                </span>
                <span className="dimension-score" style={{ color: '#818cf8' }}>
                  {report ? `${Number(report.validity_score).toFixed(1)}%` : '—'}
                </span>
              </div>
              <div className="progress-track">
                <div
                  className="progress-fill fill-validity"
                  style={{ width: `${report ? report.validity_score : 0}%` }}
                />
              </div>
            </div>

            {/* Uniqueness */}
            <div className="dimension-item">
              <div className="dimension-header">
                <span className="dimension-title">
                  <span>Uniqueness</span>
                  <span className="dimension-weight">(Weight: 20%)</span>
                </span>
                <span className="dimension-score" style={{ color: '#34d399' }}>
                  {report ? `${Number(report.uniqueness_score).toFixed(1)}%` : '—'}
                </span>
              </div>
              <div className="progress-track">
                <div
                  className="progress-fill fill-uniqueness"
                  style={{ width: `${report ? report.uniqueness_score : 0}%` }}
                />
              </div>
            </div>

            {/* Consistency */}
            <div className="dimension-item">
              <div className="dimension-header">
                <span className="dimension-title">
                  <span>Consistency</span>
                  <span className="dimension-weight">(Weight: 20%)</span>
                </span>
                <span className="dimension-score" style={{ color: '#fbbf24' }}>
                  {report ? `${Number(report.consistency_score).toFixed(1)}%` : '—'}
                </span>
              </div>
              <div className="progress-track">
                <div
                  className="progress-fill fill-consistency"
                  style={{ width: `${report ? report.consistency_score : 0}%` }}
                />
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* 5. Workspace Tabs: Cleaning Controls (V8.5) vs Quality Issues (V8.3 - V8.4) */}
      <div className="workspace-tabs" id="workspace-tabs-nav">
        <button
          id="tab-btn-clean"
          className={`tab-btn ${activeTab === 'cleaning' ? 'active' : ''}`}
          onClick={() => setActiveTab('cleaning')}
        >
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M12 20h9"/>
            <path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"/>
          </svg>
          Interactive Cleaning Pipeline
        </button>

        <button
          id="tab-btn-issues"
          className={`tab-btn ${activeTab === 'issues' ? 'active' : ''}`}
          onClick={() => setActiveTab('issues')}
        >
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="12" cy="12" r="10"/>
            <line x1="12" y1="8" x2="12" y2="12"/>
            <line x1="12" y1="16" x2="12.01" y2="16"/>
          </svg>
          Quality Issues Inspector ({issues.length})
        </button>
      </div>

      {/* Tab Content: Cleaning Controls */}
      {activeTab === 'cleaning' && (
        <section className="glass-panel cleaning-card" id="cleaning-controls-panel">
          <h3 style={{ fontSize: '1.1rem', fontWeight: 700, marginBottom: '6px' }}>
            Deterministic 13-Step Cleaning Engine
          </h3>
          <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
            Select the transformations to apply. A new Parquet dataset version will be created with lineage tracked in PostgreSQL/SQLite.
          </p>

          <div className="cleaning-options-grid">
            <label className="cleaning-option" id="opt-whitespace">
              <input
                type="checkbox"
                checked={stripWhitespace}
                onChange={(e) => setStripWhitespace(e.target.checked)}
              />
              <div className="option-text">
                <h4>Strip Whitespace & Invisible Chars</h4>
                <p>Cleans leading, trailing, and repeated whitespace across all string columns.</p>
              </div>
            </label>

            <label className="cleaning-option" id="opt-normalize-cols">
              <input
                type="checkbox"
                checked={normalizeColumns}
                onChange={(e) => setNormalizeColumns(e.target.checked)}
              />
              <div className="option-text">
                <h4>Normalize Column Names</h4>
                <p>Standardizes headers to lowercase snake_case and removes special characters.</p>
              </div>
            </label>

            <label className="cleaning-option" id="opt-deduplicate">
              <input
                type="checkbox"
                checked={dropDuplicates}
                onChange={(e) => setDropDuplicates(e.target.checked)}
              />
              <div className="option-text">
                <h4>Drop Duplicate Rows</h4>
                <p>Removes exact duplicate rows across all columns, preserving the first instance.</p>
              </div>
            </label>

            <label className="cleaning-option" id="opt-normalize-dates">
              <input
                type="checkbox"
                checked={normalizeDates}
                onChange={(e) => setNormalizeDates(e.target.checked)}
              />
              <div className="option-text">
                <h4>Standardize Date Formats</h4>
                <p>Coerces detected date columns to uniform ISO standard (YYYY-MM-DD).</p>
              </div>
            </label>
          </div>

          <div className="cleaning-actions-bar">
            <div className="cleaning-summary-note">
              🛡️ Formula injection defense is automatically enforced on export.
            </div>

            <button
              id="btn-execute-clean"
              className="btn btn-primary"
              disabled={isCleaning}
              onClick={handleRunCleaning}
            >
              {isCleaning ? (
                <>
                  <div className="spinner" />
                  Cleaning & Re-evaluating Score...
                </>
              ) : (
                <>
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <polygon points="5 3 19 12 5 21 5 3"/>
                  </svg>
                  Execute Cleaning Pipeline
                </>
              )}
            </button>
          </div>
        </section>
      )}

      {/* Tab Content: Quality Issues Inspector */}
      {activeTab === 'issues' && (
        <section className="glass-panel issues-card" id="issues-inspector-panel">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
            <h3 style={{ fontSize: '1.1rem', fontWeight: 700 }}>
              Detected Data Anomalies
            </h3>

            {/* Filter buttons */}
            <div className="issues-filter-bar" id="issue-filter-group">
              {['ALL', 'CRITICAL', 'WARNING', 'INFO'].map((sev) => (
                <button
                  key={sev}
                  id={`filter-${sev.toLowerCase()}`}
                  className={`filter-btn ${issueFilter === sev ? 'active' : ''}`}
                  onClick={() => setIssueFilter(sev)}
                >
                  {sev}
                </button>
              ))}
            </div>
          </div>

          <div className="table-wrapper">
            <table className="issues-table" id="issues-data-table">
              <thead>
                <tr>
                  <th>Severity</th>
                  <th>Category</th>
                  <th>Affected Column</th>
                  <th>Description</th>
                  <th>Rows Affected</th>
                </tr>
              </thead>
              <tbody>
                {filteredIssues.length === 0 ? (
                  <tr>
                    <td colSpan="5" style={{ textAlign: 'center', padding: '32px', color: 'var(--text-muted)' }}>
                      No {issueFilter === 'ALL' ? '' : issueFilter.toLowerCase()} issues detected for this dataset version.
                    </td>
                  </tr>
                ) : (
                  filteredIssues.map((iss, idx) => (
                    <tr key={iss.id || idx}>
                      <td>
                        <span className={`badge badge-${(iss.severity || 'info').toLowerCase()}`}>
                          {iss.severity}
                        </span>
                      </td>
                      <td className="mono" style={{ fontSize: '0.82rem', color: 'var(--text-secondary)' }}>
                        {iss.issue_type}
                      </td>
                      <td style={{ fontWeight: 600 }}>
                        {iss.column_name || '—'}
                      </td>
                      <td style={{ color: 'var(--text-secondary)' }}>
                        {iss.description}
                      </td>
                      <td className="mono" style={{ fontWeight: 700 }}>
                        {iss.rows_affected !== null && iss.rows_affected !== undefined
                          ? iss.rows_affected.toLocaleString()
                          : '—'}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {/* 6. Power BI Platform Governance Footer */}
      <footer className="footer-banner" id="governance-footer">
        <div className="powerbi-hint">
          <span className="powerbi-badge">POWER BI READY</span>
          <span>
            Metadata, cleaning jobs, and quality score lineage are stored in relational tables ready for Phase 9 Governance Analytics.
          </span>
        </div>

        <div style={{ display: 'flex', gap: '12px' }}>
          <button
            id="btn-footer-export"
            className="btn btn-primary"
            onClick={handleExportCsv}
          >
            Download Clean CSV
          </button>
        </div>
      </footer>
    </div>
  )
}
