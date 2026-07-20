import { useState, useRef } from 'react'
import { uploadFiles } from '../services/api'

export default function Upload() {
  const [status, setStatus] = useState(null)
  const [loading, setLoading] = useState(false)
  const [dragOver, setDragOver] = useState(false)
  const [selectedFiles, setSelectedFiles] = useState([])
  const inputRef = useRef(null)

  const doUpload = async (files) => {
    if (!files || files.length === 0) return
    setLoading(true)
    setStatus(null)
    try {
      const result = await uploadFiles(files)
      const failedMsg = result.failed?.length > 0
        ? ` (${result.failed.length} failed)`
        : ''
      setStatus({
        ok: true,
        message: `${result.total_uploaded} file${result.total_uploaded > 1 ? 's' : ''} uploaded and processing${failedMsg}. Ask questions in ~30 seconds.`
      })
      setSelectedFiles([])
    } catch (error) {
      setStatus({
        ok: false,
        message: 'Upload failed — check the backend connection and try again.'
      })
    } finally {
      setLoading(false)
    }
  }

  const handleChange = (e) => {
    const files = Array.from(e.target.files)
    setSelectedFiles(files)
  }

  const handleDrop = (e) => {
    e.preventDefault()
    setDragOver(false)
    const files = Array.from(e.dataTransfer.files)
    setSelectedFiles(files)
  }

  const handleUploadClick = () => {
    if (selectedFiles.length > 0) {
      doUpload(selectedFiles)
    }
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
          <strong>Drop files</strong> or click to browse
        </div>
        <div className="dropzone__hint">PDF · CSV · XLSX · JPG · PNG · Select multiple files</div>

        <input
          ref={inputRef}
          type="file"
          accept=".pdf,.csv,.xlsx,.jpg,.jpeg,.png"
          multiple
          onChange={handleChange}
          disabled={loading}
          style={{ display: 'none' }}
        />
      </div>

      {/* Selected files preview */}
      {selectedFiles.length > 0 && !loading && (
        <div className="upload-page__preview">
          <p className="upload-page__preview-title">
            {selectedFiles.length} file{selectedFiles.length > 1 ? 's' : ''} selected:
          </p>
          <ul className="upload-page__file-list">
            {selectedFiles.map((f, i) => (
              <li key={i} className="upload-page__file-item">
                📄 {f.name}
                <span className="upload-page__file-size">
                  ({(f.size / 1024).toFixed(1)} KB)
                </span>
              </li>
            ))}
          </ul>
          <button
            className="btn btn--primary"
            onClick={handleUploadClick}
            disabled={loading}
          >
            Upload {selectedFiles.length} file{selectedFiles.length > 1 ? 's' : ''}
          </button>
        </div>
      )}

      {loading && (
        <p className="upload-page__status">
          ⏳ Uploading and processing {selectedFiles.length > 0 ? selectedFiles.length : ''} file{selectedFiles.length > 1 ? 's' : ''}…
        </p>
      )}

      {status && (
        <p className={'upload-page__status' + (status.ok ? ' upload-page__status--ok' : ' upload-page__status--error')}>
          {status.ok ? '✓ ' : '✕ '}{status.message}
        </p>
      )}
    </div>
  )
}