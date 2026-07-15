import { useState, useRef } from 'react'
import { uploadFile } from '../services/api'

export default function Upload() {
  const [status, setStatus] = useState(null) // { ok: bool, message: string } | null
  const [loading, setLoading] = useState(false)
  const [dragOver, setDragOver] = useState(false)
  const inputRef = useRef(null)

  const doUpload = async (file) => {
    if (!file) return
    setLoading(true)
    setStatus(null)
    try {
      const result = await uploadFile(file)
      setStatus({ ok: true, message: result.message })
    } catch (error) {
      setStatus({ ok: false, message: 'Upload failed — check the backend connection and try again.' })
    } finally {
      setLoading(false)
    }
  }

  const handleChange = (e) => doUpload(e.target.files[0])

  const handleDrop = (e) => {
    e.preventDefault()
    setDragOver(false)
    doUpload(e.dataTransfer.files[0])
  }

  return (
    <div className="upload-page blueprint-grid">
      <span className="eyebrow">DOCUMENT INTAKE</span>
      <h2 className="upload-page__title">Feed the knowledge graph</h2>
      <p className="upload-page__subtitle">
        PDFs, scanned inspection forms, and CSV logs are ingested, entity-tagged,
        and linked into the graph automatically.
      </p>

      <div
        className={'dropzone' + (dragOver ? ' dropzone--active' : '')}
        onDragOver={(e) => { e.preventDefault(); setDragOver(true) }}
        onDragLeave={() => setDragOver(false)}
        onDrop={handleDrop}
        onClick={() => inputRef.current?.click()}
      >
        <div className="dropzone__icon">⇧</div>
        <div className="dropzone__text">
          <strong>Drop a file</strong> or click to browse
        </div>
        <div className="dropzone__hint">PDF · CSV · XLSX · JPG · PNG</div>

        <input
          ref={inputRef}
          type="file"
          accept=".pdf,.csv,.xlsx,.jpg,.jpeg,.png"
          onChange={handleChange}
          disabled={loading}
          style={{ display: 'none' }}
        />
      </div>

      {loading && <p className="upload-page__status">Processing…</p>}

      {status && (
        <p className={'upload-page__status' + (status.ok ? ' upload-page__status--ok' : ' upload-page__status--error')}>
          {status.ok ? '✓ ' : '✕ '}{status.message}
        </p>
      )}
    </div>
  )
}
