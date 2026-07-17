import { useState } from 'react'
import { runRCA } from '../services/api'
import Gauge from '../components/Gauge'

const SEVERITY_META = {
  LOW:      { tone: 'low',      label: 'LOW' },
  MEDIUM:   { tone: 'medium',   label: 'MEDIUM' },
  HIGH:     { tone: 'high',     label: 'HIGH' },
  CRITICAL: { tone: 'critical', label: 'CRITICAL' }
}

export default function RCA() {
  const [tag, setTag] = useState('')
  const [report, setReport] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const analyze = async () => {
    if (!tag.trim()) return
    setLoading(true)
    setError(null)
    setReport(null)
    try {
      const result = await runRCA(tag.trim().toUpperCase())
      setReport(result)
    } catch (e) {
      setError('RCA agent could not be reached — confirm the backend is running and try again.')
    } finally {
      setLoading(false)
    }
  }

  const handleKeyPress = (e) => {
    if (e.key === 'Enter') analyze()
  }

  const severity = report ? (SEVERITY_META[report.severity] || SEVERITY_META.MEDIUM) : null

  return (
    <div className="rca-page blueprint-grid">
      <span className="eyebrow">MAINTENANCE INTELLIGENCE</span>
      <h2 className="rca__title">Root cause analysis</h2>
      <p className="rca__subtitle">
        Enter an equipment tag to fuse work-order history, OEM specs, and sensor
        trends into a cited failure investigation.
      </p>

      <div className="rca__console">
        <div className="rca__input-row">
          <input
            className="rca__input"
            value={tag}
            onChange={e => setTag(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="Enter equipment tag, e.g. P-104"
            disabled={loading}
          />
          <button
            className="btn btn--primary"
            onClick={analyze}
            disabled={loading || !tag.trim()}
          >
            {loading ? 'Analyzing…' : 'Analyze'}
          </button>
        </div>

        <div className="rca__quick-tags">
          {['P-104', 'P-105', 'BL-07', 'V-22'].map(t => (
            <button
              key={t}
              className="suggestion-chip"
              onClick={() => setTag(t)}
              disabled={loading}
            >
              {t}
            </button>
          ))}
        </div>
      </div>

      {loading && (
        <div className="rca__loading">
          <Gauge value={50} sweeping size={56} tone="amber" label="" />
          <div className="rca__loading-steps">
            <p><span className="rca__loading-dot" />Gathering evidence from all documents</p>
            <p><span className="rca__loading-dot" />Running multi-step failure analysis</p>
            <p><span className="rca__loading-dot" />Generating cited report</p>
          </div>
        </div>
      )}

      {error && <div className="rca__error">{error}</div>}

      {report && (
        <div className="rca__report">
          <div className="rca__report-header">
            <div>
              <span className="rca__report-eyebrow">EQUIPMENT</span>
              <h3 className="rca__equipment-tag">{report.equipment}</h3>
              <p className="rca__failure-summary">{report.failure_summary}</p>
            </div>
            <span className={`severity-badge severity-badge--${severity.tone}`}>
              <span className="severity-badge__dot" />
              {severity.label}
            </span>
          </div>

          <div className="rca__cards">

            <div className="rca__card">
              <h4 className="rca__card-title">Immediate cause</h4>
              <p className="rca__card-body">{report.immediate_cause}</p>
            </div>

            <div className="rca__card rca__card--highlight">
              <h4 className="rca__card-title rca__card-title--amber">Root cause</h4>
              <p className="rca__card-body">{report.root_cause}</p>
            </div>

            <div className="rca__card">
              <h4 className="rca__card-title">OEM spec vs. actual</h4>
              <div className="rca__compare">
                <div className="rca__compare-row">
                  <span className="rca__compare-label">OEM SPEC</span>
                  <span className="rca__compare-value">{report.oem_vs_actual?.oem_spec}</span>
                </div>
                <div className="rca__compare-row">
                  <span className="rca__compare-label">WHAT HAPPENED</span>
                  <span className="rca__compare-value">{report.oem_vs_actual?.what_happened}</span>
                </div>
                <div className="rca__compare-row">
                  <span className="rca__compare-label">GAP</span>
                  <span className="rca__compare-value rca__compare-value--gap">
                    {report.oem_vs_actual?.gap}
                  </span>
                </div>
              </div>
            </div>

            <div className="rca__card">
              <h4 className="rca__card-title">Contributing factors</h4>
              <ul className="rca__list">
                {report.contributing_factors?.map((f, i) => (
                  <li key={i}>{f}</li>
                ))}
              </ul>
            </div>

            <div className="rca__card">
              <h4 className="rca__card-title">Timeline</h4>
              <p className="rca__card-body">{report.timeline}</p>
            </div>

            <div className="rca__card">
              <h4 className="rca__card-title">Similar past failures</h4>
              {report.similar_past_failures?.length > 0
                ? (
                  <ul className="rca__list">
                    {report.similar_past_failures.map((f, i) => <li key={i}>{f}</li>)}
                  </ul>
                )
                : <p className="rca__card-body rca__card-body--muted">No similar past failures found in the indexed documents.</p>
              }
            </div>

            <div className="rca__card rca__card--recommendations">
              <h4 className="rca__card-title rca__card-title--verdigris">Recommendations</h4>
              <ol className="rca__list rca__list--numbered">
                {report.recommendations?.map((r, i) => (
                  <li key={i}>{r}</li>
                ))}
              </ol>
            </div>

            <div className="rca__card">
              <h4 className="rca__card-title">Production impact</h4>
              <p className="rca__card-body">{report.production_impact}</p>
            </div>

          </div>
        </div>
      )}
    </div>
  )
}