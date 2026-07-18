import { useState, useEffect } from 'react'
import { getFullSummary, summarizeTopic } from '../services/api'
import SourceCard from '../components/SourceCard'
import Loader from '../components/Loader'

export default function Summary() {
  const [summary, setSummary] = useState(null)
  const [summaryLoading, setSummaryLoading] = useState(false)
  const [summaryError, setSummaryError] = useState(null)

  const [topic, setTopic] = useState('')
  const [topicResult, setTopicResult] = useState(null)
  const [topicLoading, setTopicLoading] = useState(false)
  const [topicError, setTopicError] = useState(null)

  const loadSummary = async () => {
    setSummaryLoading(true)
    setSummaryError(null)
    try {
      const result = await getFullSummary()
      setSummary(result)
    } catch (e) {
      setSummaryError('Could not reach the backend — confirm the API is running and try again.')
    } finally {
      setSummaryLoading(false)
    }
  }

  useEffect(() => {
    loadSummary()
  }, [])

  const runTopicSummary = async (value) => {
    const query = (value ?? topic).trim()
    if (!query || topicLoading) return
    setTopicLoading(true)
    setTopicError(null)
    setTopicResult(null)
    try {
      const result = await summarizeTopic(query)
      setTopicResult(result)
    } catch (e) {
      setTopicError('Could not reach the backend — confirm the API is running and try again.')
    } finally {
      setTopicLoading(false)
    }
  }

  const handleKeyPress = (e) => {
    if (e.key === 'Enter') runTopicSummary()
  }

  const suggestions = [
    'P-104 maintenance history',
    'Compliance and regulatory status',
    'All equipment failures',
    'Near miss incidents',
    'Boiler BL-07 status'
  ]

  return (
    <div className="intel-page blueprint-grid">
      <div className="copilot__header">
        <span className="eyebrow">KNOWLEDGE SUMMARY</span>
        <h2 className="copilot__title">Document intelligence summary</h2>
        <p className="intel-page__subtitle">Structured overview of all indexed plant documents.</p>
      </div>

      <div className="readout-strip readout-strip--static">
        <div className="readout">
          <span className="readout__value">10</span>
          <span className="readout__label">DOCUMENTS INDEXED</span>
        </div>
        <div className="readout-strip__divider" />
        <div className="readout">
          <span className="readout__value">205</span>
          <span className="readout__label">ENTITIES EXTRACTED</span>
        </div>
        <div className="readout-strip__divider" />
        <div className="readout">
          <span className="readout__value">26</span>
          <span className="readout__label">KNOWLEDGE CHUNKS</span>
        </div>
      </div>

      <div className="intel-section">
        <div className="copilot__panel copilot__panel--static">
          {summaryLoading && (
            <div className="intel-card__loading">
              <Loader label="Summarising all indexed documents…" />
            </div>
          )}

          {!summaryLoading && summaryError && (
            <div className="msg-bubble msg-bubble--error">{summaryError}</div>
          )}

          {!summaryLoading && summary && (
            <>
              <div className="intel-card">
                <p className="intel-card__body">{summary.answer}</p>
              </div>

              {summary.sources && summary.sources.length > 0 && (
                <div className="msg-sources intel-card__sources">
                  {summary.sources.map((source, i) => (
                    <SourceCard key={i} filename={source} />
                  ))}
                </div>
              )}

              <div className="intel-card__meta">
                <span />
                <button className="btn btn--ghost" onClick={loadSummary} disabled={summaryLoading}>
                  Regenerate Summary
                </button>
              </div>
            </>
          )}
        </div>
      </div>

      <div className="intel-section">
        <h3 className="intel-section-title">Ask for specific summary</h3>

        <div className="copilot__panel copilot__panel--static">
          <div className="copilot__input-row copilot__input-row--static">
            <input
              className="copilot__input"
              value={topic}
              onChange={e => setTopic(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="Enter topic e.g. P-104 failure history"
              disabled={topicLoading}
            />
            <button
              className="btn btn--primary"
              onClick={() => runTopicSummary()}
              disabled={topicLoading || !topic.trim()}
            >
              {topicLoading ? 'Summarizing…' : 'Summarize'}
            </button>
          </div>

          <div className="suggestions suggestions--static">
            {suggestions.map((s, i) => (
              <button
                key={i}
                className="suggestion-chip"
                onClick={() => { setTopic(s); runTopicSummary(s) }}
                disabled={topicLoading}
              >
                {s}
              </button>
            ))}
          </div>

          {topicLoading && (
            <div className="intel-card__loading intel-card__loading--inline">
              <Loader label="Summarizing topic…" />
            </div>
          )}

          {!topicLoading && topicError && (
            <div className="msg-bubble msg-bubble--error intel-card__loading--inline">{topicError}</div>
          )}

          {!topicLoading && topicResult && (
            <div className="intel-card intel-card--inline">
              <p className="intel-card__body">{topicResult.answer}</p>
              {topicResult.sources && topicResult.sources.length > 0 && (
                <div className="msg-sources intel-card__sources">
                  {topicResult.sources.map((source, i) => (
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
