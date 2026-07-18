import { useState, useEffect } from 'react'
import { getSafetyReport, checkEquipmentSafety } from '../services/api'
import SourceCard from '../components/SourceCard'
import Loader from '../components/Loader'

export default function Safety() {
  const [report, setReport] = useState(null)
  const [reportLoading, setReportLoading] = useState(false)
  const [reportError, setReportError] = useState(null)

  const [tag, setTag] = useState('')
  const [checkResult, setCheckResult] = useState(null)
  const [checkLoading, setCheckLoading] = useState(false)
  const [checkError, setCheckError] = useState(null)

  const loadReport = async () => {
    setReportLoading(true)
    setReportError(null)
    try {
      const result = await getSafetyReport()
      setReport(result)
    } catch (e) {
      setReportError('Could not reach the backend — confirm the API is running and try again.')
    } finally {
      setReportLoading(false)
    }
  }

  useEffect(() => {
    loadReport()
  }, [])

  const checkSafety = async () => {
    if (!tag.trim() || checkLoading) return
    setCheckLoading(true)
    setCheckError(null)
    setCheckResult(null)
    try {
      const result = await checkEquipmentSafety(tag.trim().toUpperCase())
      setCheckResult(result)
    } catch (e) {
      setCheckError('Could not reach the backend — confirm the API is running and try again.')
    } finally {
      setCheckLoading(false)
    }
  }

  const handleKeyPress = (e) => {
    if (e.key === 'Enter') checkSafety()
  }

  return (
    <div className="intel-page blueprint-grid">
      <div className="copilot__header">
        <span className="eyebrow">PLANT SAFETY INTELLIGENCE</span>
        <h2 className="copilot__title">Safety status dashboard</h2>
        <p className="intel-page__subtitle">Real-time safety analysis from all indexed documents.</p>
      </div>

      <div className="intel-section">
        <div className="copilot__panel copilot__panel--static">
          {reportLoading && (
            <div className="intel-card__loading">
              <Loader label="Analysing all documents for safety issues…" />
            </div>
          )}

          {!reportLoading && reportError && (
            <div className="msg-bubble msg-bubble--error">{reportError}</div>
          )}

          {!reportLoading && report && (
            <>
              <div className="intel-card">
                <p className="intel-card__body">{report.safety_report}</p>
              </div>

              {report.sources && report.sources.length > 0 && (
                <div className="msg-sources intel-card__sources">
                  {report.sources.map((source, i) => (
                    <SourceCard key={i} filename={source} />
                  ))}
                </div>
              )}

              <div className="intel-card__meta">
                <span className="timestamp">
                  {report.generated_at ? `Generated ${report.generated_at}` : ''}
                </span>
                <button className="btn btn--ghost" onClick={loadReport} disabled={reportLoading}>
                  Refresh
                </button>
              </div>
            </>
          )}
        </div>
      </div>

      <div className="intel-section">
        <h3 className="intel-section-title">Check specific equipment</h3>

        <div className="copilot__panel copilot__panel--static">
          <div className="copilot__input-row copilot__input-row--static">
            <input
              className="copilot__input"
              value={tag}
              onChange={e => setTag(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="Enter equipment tag e.g. P-104, BL-07, V-22"
              disabled={checkLoading}
            />
            <button
              className="btn btn--primary"
              onClick={checkSafety}
              disabled={checkLoading || !tag.trim()}
            >
              {checkLoading ? 'Checking…' : 'Check Safety'}
            </button>
          </div>

          <div className="suggestions suggestions--static">
            {['P-104', 'P-105', 'BL-07', 'V-22', 'HX-11'].map(t => (
              <button
                key={t}
                className="suggestion-chip"
                onClick={() => setTag(t)}
                disabled={checkLoading}
              >
                {t}
              </button>
            ))}
          </div>

          {checkLoading && (
            <div className="intel-card__loading intel-card__loading--inline">
              <Loader label="Checking equipment safety status…" />
            </div>
          )}

          {!checkLoading && checkError && (
            <div className="msg-bubble msg-bubble--error intel-card__loading--inline">{checkError}</div>
          )}

          {!checkLoading && checkResult && (
            <div className="intel-card intel-card--inline">
              <p className="intel-card__body">{checkResult.answer}</p>
              {checkResult.sources && checkResult.sources.length > 0 && (
                <div className="msg-sources intel-card__sources">
                  {checkResult.sources.map((source, i) => (
                    <SourceCard key={i} filename={source} />
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
