import { useState, useCallback } from 'react'

const API = '/api'

export default function App() {
  const [zipFile, setZipFile] = useState(null)
  const [sheetFile, setSheetFile] = useState(null)
  const [threshold, setThreshold] = useState(70)
  const [preview, setPreview] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const handleZip = useCallback((e) => {
    const f = e.target.files?.[0]
    setZipFile(f || null)
    setPreview(null)
    setError(null)
  }, [])

  const handleSheet = useCallback((e) => {
    const f = e.target.files?.[0]
    setSheetFile(f || null)
    setPreview(null)
    setError(null)
  }, [])

  const fetchPreview = useCallback(async () => {
    if (!zipFile || !sheetFile) {
      setError('Please select both a creatives ZIP and a T-sheet (Excel or CSV).')
      return
    }
    setLoading(true)
    setError(null)
    setPreview(null)
    try {
      const form = new FormData()
      form.append('zip_file', zipFile)
      form.append('sheet', sheetFile)
      form.append('threshold', (threshold / 100).toString())
      const r = await fetch(`${API}/preview`, {
        method: 'POST',
        body: form,
      })
      if (!r.ok) {
        const t = await r.text()
        throw new Error(t || r.statusText)
      }
      const data = await r.json()
      setPreview(data)
    } catch (err) {
      setError(err.message || 'Preview failed.')
    } finally {
      setLoading(false)
    }
  }, [zipFile, sheetFile, threshold])

  const downloadRenamedZip = useCallback(async () => {
    if (!zipFile || !sheetFile) return
    setLoading(true)
    setError(null)
    try {
      const form = new FormData()
      form.append('zip_file', zipFile)
      form.append('sheet', sheetFile)
      form.append('threshold', (threshold / 100).toString())
      const r = await fetch(`${API}/rename`, { method: 'POST', body: form })
      if (!r.ok) throw new Error(await r.text())
      const blob = await r.blob()
      const a = document.createElement('a')
      a.href = URL.createObjectURL(blob)
      a.download = 'renamed-creatives.zip'
      a.click()
      URL.revokeObjectURL(a.href)
    } catch (err) {
      setError(err.message || 'Download failed.')
    } finally {
      setLoading(false)
    }
  }, [zipFile, sheetFile, threshold])

  const downloadLog = useCallback(async () => {
    if (!zipFile || !sheetFile) return
    setLoading(true)
    setError(null)
    try {
      const form = new FormData()
      form.append('zip_file', zipFile)
      form.append('sheet', sheetFile)
      form.append('threshold', (threshold / 100).toString())
      const r = await fetch(`${API}/log`, { method: 'POST', body: form })
      if (!r.ok) throw new Error(await r.text())
      const data = await r.json()
      const blob = new Blob([data.csv], { type: 'text/csv' })
      const a = document.createElement('a')
      a.href = URL.createObjectURL(blob)
      a.download = 'rename-log.csv'
      a.click()
      URL.revokeObjectURL(a.href)
    } catch (err) {
      setError(err.message || 'Log download failed.')
    } finally {
      setLoading(false)
    }
  }, [zipFile, sheetFile, threshold])

  const list = preview?.preview ?? []
  const lowConfidence = list.filter((r) => r.score < threshold)
  const highConfidence = list.filter((r) => r.score >= threshold)

  return (
    <div style={styles.container}>
      <header style={styles.header}>
        <h1 style={styles.title}>CM360 Creative Renamer</h1>
        <p style={styles.subtitle}>Upload creatives ZIP + T-sheet → preview → download renamed ZIP & log</p>
      </header>

      <section style={styles.section}>
        <h2 style={styles.sectionTitle}>1. Upload files</h2>
        <div style={styles.uploadRow}>
          <label style={styles.label}>
            Creatives (ZIP)
            <input type="file" accept=".zip" onChange={handleZip} style={styles.input} />
            <span style={styles.fileName}>{zipFile?.name || 'No file'}</span>
          </label>
          <label style={styles.label}>
            T-sheet (Excel / CSV)
            <input type="file" accept=".xlsx,.xls,.csv" onChange={handleSheet} style={styles.input} />
            <span style={styles.fileName}>{sheetFile?.name || 'No file'}</span>
          </label>
        </div>
      </section>

      <section style={styles.section}>
        <h2 style={styles.sectionTitle}>2. Confidence threshold</h2>
        <div style={styles.sliderRow}>
          <input
            type="range"
            min={50}
            max={95}
            value={threshold}
            onChange={(e) => setThreshold(Number(e.target.value))}
            style={styles.slider}
          />
          <span style={styles.thresholdLabel}>{threshold}%</span>
        </div>
        <p style={styles.hint}>Matches below this % will still get a best guess but are flagged for review.</p>
      </section>

      <section style={styles.section}>
        <h2 style={styles.sectionTitle}>3. Preview & download</h2>
        <div style={styles.buttonRow}>
          <button onClick={fetchPreview} disabled={loading || !zipFile || !sheetFile} style={styles.button}>
            {loading ? '…' : 'Preview mapping'}
          </button>
          <button
            onClick={downloadRenamedZip}
            disabled={loading || !zipFile || !sheetFile}
            style={{ ...styles.button, ...styles.buttonPrimary }}
          >
            Download renamed ZIP
          </button>
          <button
            onClick={downloadLog}
            disabled={loading || !zipFile || !sheetFile}
            style={styles.button}
          >
            Download CSV log
          </button>
        </div>
        {error && <p style={styles.error}>{error}</p>}
      </section>

      {preview && (
        <section style={styles.section}>
          <h2 style={styles.sectionTitle}>Preview</h2>
          <p style={styles.meta}>
            {list.length} files · {preview.sheet_names_count} names in sheet ·{' '}
            {highConfidence.length} ≥{threshold}% · {lowConfidence.length} &lt;{threshold}% (review)
          </p>
          <div style={styles.tableWrap}>
            <table style={styles.table}>
              <thead>
                <tr>
                  <th style={styles.th}>Original file</th>
                  <th style={styles.th}>New name</th>
                  <th style={styles.th}>Match %</th>
                </tr>
              </thead>
              <tbody>
                {list.map((row, i) => {
                  const newName = (row.matched_name || row.file_stem) + (row.extension || '')
                  const isLow = row.score < threshold
                  return (
                    <tr key={i} style={isLow ? { ...styles.tr, background: 'rgba(248,113,113,0.15)' } : styles.tr}>
                      <td style={styles.td}>{row.file_path}</td>
                      <td style={styles.td}>{newName}</td>
                      <td style={styles.td}>{row.score}%</td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </section>
      )}
    </div>
  )
}

const styles = {
  container: {
    maxWidth: 960,
    margin: '0 auto',
    padding: '2rem 1rem',
  },
  header: {
    marginBottom: '2rem',
    textAlign: 'center',
  },
  title: {
    fontSize: '1.75rem',
    fontWeight: 700,
    margin: 0,
    color: '#f8fafc',
  },
  subtitle: {
    margin: '0.5rem 0 0',
    color: '#94a3b8',
    fontSize: '0.95rem',
  },
  section: {
    marginBottom: '2rem',
  },
  sectionTitle: {
    fontSize: '1.1rem',
    fontWeight: 600,
    marginBottom: '0.75rem',
    color: '#e2e8f0',
  },
  uploadRow: {
    display: 'flex',
    flexWrap: 'wrap',
    gap: '1.5rem',
  },
  label: {
    display: 'flex',
    flexDirection: 'column',
    gap: '0.25rem',
    cursor: 'pointer',
  },
  input: {
    padding: '0.5rem',
    borderRadius: 8,
    border: '1px solid #334155',
    background: '#1e293b',
    color: '#e2e8f0',
  },
  fileName: {
    fontSize: '0.85rem',
    color: '#94a3b8',
  },
  sliderRow: {
    display: 'flex',
    alignItems: 'center',
    gap: '1rem',
  },
  slider: {
    width: 200,
    accentColor: '#3b82f6',
  },
  thresholdLabel: {
    fontWeight: 600,
    minWidth: 48,
  },
  hint: {
    margin: '0.5rem 0 0',
    fontSize: '0.85rem',
    color: '#94a3b8',
  },
  buttonRow: {
    display: 'flex',
    flexWrap: 'wrap',
    gap: '0.75rem',
  },
  button: {
    padding: '0.6rem 1rem',
    borderRadius: 8,
    border: '1px solid #475569',
    background: '#334155',
    color: '#e2e8f0',
    cursor: 'pointer',
    fontWeight: 500,
  },
  buttonPrimary: {
    background: '#3b82f6',
    borderColor: '#3b82f6',
    color: '#fff',
  },
  error: {
    marginTop: '0.75rem',
    color: '#f87171',
    fontSize: '0.9rem',
  },
  meta: {
    fontSize: '0.9rem',
    color: '#94a3b8',
    marginBottom: '0.75rem',
  },
  tableWrap: {
    overflowX: 'auto',
    borderRadius: 8,
    border: '1px solid #334155',
  },
  table: {
    width: '100%',
    borderCollapse: 'collapse',
    fontSize: '0.85rem',
  },
  th: {
    textAlign: 'left',
    padding: '0.6rem 0.75rem',
    background: '#1e293b',
    color: '#94a3b8',
    fontWeight: 600,
  },
  tr: {},
  td: {
    padding: '0.5rem 0.75rem',
    borderTop: '1px solid #334155',
  },
}
