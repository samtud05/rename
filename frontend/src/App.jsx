import { useState, useCallback } from 'react'

const API = '/api'

function parseErrorResponse(text) {
  try {
    const j = JSON.parse(text)
    if (j && typeof j.detail === 'string') return j.detail
    if (j && Array.isArray(j.detail)) return j.detail.map((d) => d.msg || String(d)).join('. ')
  } catch (_) {}
  return text || 'Something went wrong.'
}

export default function App() {
  const [view, setView] = useState('rename') // 'rename' | 'compare'
  const [zipFile, setZipFile] = useState(null)
  const [sheetFile, setSheetFile] = useState(null)
  const DEFAULT_THRESHOLD = 0.7
  const [sheetName, setSheetName] = useState('')
  const [columnHeader, setColumnHeader] = useState('')
  const [preview, setPreview] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [compareZip1, setCompareZip1] = useState(null)
  const [compareZip2, setCompareZip2] = useState(null)
  const [compareResult, setCompareResult] = useState(null)
  const [compareLoading, setCompareLoading] = useState(false)
  const [compareError, setCompareError] = useState(null)

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
    if (!zipFile.name.toLowerCase().endsWith('.zip')) {
      setError('Creatives file must be a ZIP archive.')
      return
    }
    const sheetLower = sheetFile.name.toLowerCase()
    if (!sheetLower.endsWith('.xlsx') && !sheetLower.endsWith('.xls') && !sheetLower.endsWith('.csv')) {
      setError('T-sheet must be an Excel file (.xlsx, .xls) or CSV.')
      return
    }
    setLoading(true)
    setError(null)
    setPreview(null)
    try {
      const form = new FormData()
      form.append('zip_file', zipFile)
      form.append('sheet', sheetFile)
      form.append('threshold', DEFAULT_THRESHOLD.toString())
      if (sheetName.trim()) form.append('sheet_name', sheetName.trim())
      if (columnHeader.trim()) form.append('column_header', columnHeader.trim())
      const r = await fetch(`${API}/preview`, {
        method: 'POST',
        body: form,
      })
      if (!r.ok) {
        const t = await r.text()
        throw new Error(parseErrorResponse(t))
      }
      const data = await r.json()
      setPreview(data)
    } catch (err) {
      setError(err.message || 'Preview failed.')
    } finally {
      setLoading(false)
    }
  }, [zipFile, sheetFile, sheetName, columnHeader])

  const downloadRenamedZip = useCallback(async () => {
    if (!zipFile || !sheetFile) return
    setLoading(true)
    setError(null)
    try {
      const form = new FormData()
      form.append('zip_file', zipFile)
      form.append('sheet', sheetFile)
      form.append('threshold', DEFAULT_THRESHOLD.toString())
      if (sheetName.trim()) form.append('sheet_name', sheetName.trim())
      if (columnHeader.trim()) form.append('column_header', columnHeader.trim())
      const r = await fetch(`${API}/rename`, { method: 'POST', body: form })
      if (!r.ok) throw new Error(parseErrorResponse(await r.text()))
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
  }, [zipFile, sheetFile, sheetName, columnHeader])

  const downloadLog = useCallback(async () => {
    if (!zipFile || !sheetFile) return
    setLoading(true)
    setError(null)
    try {
      const form = new FormData()
      form.append('zip_file', zipFile)
      form.append('sheet', sheetFile)
      form.append('threshold', DEFAULT_THRESHOLD.toString())
      if (sheetName.trim()) form.append('sheet_name', sheetName.trim())
      if (columnHeader.trim()) form.append('column_header', columnHeader.trim())
      const r = await fetch(`${API}/log`, { method: 'POST', body: form })
      if (!r.ok) throw new Error(parseErrorResponse(await r.text()))
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
  }, [zipFile, sheetFile, sheetName, columnHeader])

  const runCompare = useCallback(async () => {
    if (!compareZip1 || !compareZip2) {
      setCompareError('Please select both ZIPs to compare.')
      return
    }
    setCompareLoading(true)
    setCompareError(null)
    setCompareResult(null)
    try {
      const form = new FormData()
      form.append('zip1', compareZip1)
      form.append('zip2', compareZip2)
      const r = await fetch(`${API}/compare`, { method: 'POST', body: form })
      if (!r.ok) throw new Error(parseErrorResponse(await r.text()))
      const data = await r.json()
      setCompareResult(data)
    } catch (err) {
      setCompareError(err.message || 'Compare failed.')
    } finally {
      setCompareLoading(false)
    }
  }, [compareZip1, compareZip2])

  const list = preview?.preview ?? []
  const thresholdNum = 70 // used only for highlighting low-confidence rows in preview

  return (
    <div style={styles.layout}>
      <aside style={styles.sidebar}>
        <div style={styles.sidebarHeader}>
          <h1 style={styles.sidebarTitle}>CM360 Tools</h1>
        </div>
        <nav style={styles.nav}>
          <button
            type="button"
            style={view === 'rename' ? { ...styles.navItem, ...styles.navItemActive } : styles.navItem}
            onClick={() => setView('rename')}
          >
            Rename creatives
          </button>
          <button
            type="button"
            style={view === 'compare' ? { ...styles.navItem, ...styles.navItemActive } : styles.navItem}
            onClick={() => setView('compare')}
          >
            Compare ZIPs
          </button>
        </nav>
      </aside>

      <main style={styles.main}>
        {view === 'rename' && (
          <>
            <header style={styles.header}>
              <h2 style={styles.title}>Rename creatives</h2>
              <p style={styles.subtitle}>Upload creatives ZIP + T-sheet → preview → download renamed ZIP & log</p>
            </header>

            <section style={styles.section}>
              <h3 style={styles.sectionTitle}>Upload files</h3>
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
        <div style={styles.optionalRow}>
          <label style={styles.label}>
            Sheet name (Excel only, optional)
            <input
              type="text"
              placeholder="e.g. T1"
              value={sheetName}
              onChange={(e) => setSheetName(e.target.value)}
              style={styles.textInput}
            />
          </label>
          <label style={styles.label}>
            Column header (optional)
            <input
              type="text"
              placeholder="e.g. Creative Name"
              value={columnHeader}
              onChange={(e) => setColumnHeader(e.target.value)}
              style={styles.textInput}
            />
          </label>
        </div>
        <p style={styles.hint}>Leave blank to auto-detect the Creative Name column.</p>
      </section>

      <section style={styles.section}>
        <h3 style={styles.sectionTitle}>Preview & download</h3>
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
          <h3 style={styles.sectionTitle}>Preview</h3>
          <p style={styles.meta}>
            {list.length} files · {preview.sheet_names_count} names in sheet
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
                  const isLow = row.score < thresholdNum
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
          </>
        )}

        {view === 'compare' && (
          <>
            <header style={styles.header}>
              <h2 style={styles.title}>Compare two ZIPs</h2>
              <p style={styles.subtitle}>Compare your updated ZIP with the tool&apos;s renamed ZIP</p>
            </header>

      <section style={styles.section}>
        <h3 style={styles.sectionTitle}>Select ZIPs</h3>
        <p style={styles.hint}>
          Compare your updated ZIP with the tool&apos;s renamed ZIP: see which files exist only in one, which match (same content), and which have the same name but different content.
        </p>
        <div style={styles.uploadRow}>
          <label style={styles.label}>
            ZIP 1 (e.g. your updated)
            <input
              type="file"
              accept=".zip"
              onChange={(e) => {
                setCompareZip1(e.target.files?.[0] || null)
                setCompareResult(null)
                setCompareError(null)
              }}
              style={styles.input}
            />
            <span style={styles.fileName}>{compareZip1?.name || 'No file'}</span>
          </label>
          <label style={styles.label}>
            ZIP 2 (e.g. tool output)
            <input
              type="file"
              accept=".zip"
              onChange={(e) => {
                setCompareZip2(e.target.files?.[0] || null)
                setCompareResult(null)
                setCompareError(null)
              }}
              style={styles.input}
            />
            <span style={styles.fileName}>{compareZip2?.name || 'No file'}</span>
          </label>
        </div>
        <div style={styles.buttonRow}>
          <button
            onClick={runCompare}
            disabled={compareLoading || !compareZip1 || !compareZip2}
            style={styles.button}
          >
            {compareLoading ? '…' : 'Compare'}
          </button>
        </div>
        {compareError && <p style={styles.error}>{compareError}</p>}
        {compareResult && (
          <div style={styles.compareResult}>
            <p style={styles.meta}>
              Only in ZIP 1: {compareResult.summary.only_in_1_count} · Only in ZIP 2: {compareResult.summary.only_in_2_count} · Same content: {compareResult.summary.same_content_count} · Same name, different content: {compareResult.summary.different_content_count}
            </p>
            <div style={styles.compareGrid}>
              <div style={styles.compareCol}>
                <h3 style={styles.compareColTitle}>Only in ZIP 1</h3>
                <ul style={styles.compareList}>
                  {compareResult.only_in_1.length ? compareResult.only_in_1.map((f, i) => <li key={i} style={styles.compareLi}>{f}</li>) : <li style={styles.compareLi}>(none)</li>}
                </ul>
              </div>
              <div style={styles.compareCol}>
                <h3 style={styles.compareColTitle}>Only in ZIP 2</h3>
                <ul style={styles.compareList}>
                  {compareResult.only_in_2.length ? compareResult.only_in_2.map((f, i) => <li key={i} style={styles.compareLi}>{f}</li>) : <li style={styles.compareLi}>(none)</li>}
                </ul>
              </div>
              <div style={styles.compareCol}>
                <h3 style={styles.compareColTitle}>Same content</h3>
                <ul style={styles.compareList}>
                  {compareResult.same_content.length ? compareResult.same_content.map((f, i) => <li key={i} style={styles.compareLi}>{f}</li>) : <li style={styles.compareLi}>(none)</li>}
                </ul>
              </div>
              <div style={styles.compareCol}>
                <h3 style={{ ...styles.compareColTitle, color: '#fbbf24' }}>Same name, different content</h3>
                <ul style={styles.compareList}>
                  {compareResult.different_content.length ? compareResult.different_content.map((f, i) => <li key={i} style={styles.compareLi}>{f}</li>) : <li style={styles.compareLi}>(none)</li>}
                </ul>
              </div>
            </div>
          </div>
        )}
      </section>
          </>
        )}
      </main>
    </div>
  )
}

const styles = {
  layout: {
    display: 'flex',
    minHeight: '100vh',
    background: '#0f172a',
  },
  sidebar: {
    width: 220,
    flexShrink: 0,
    background: '#1e293b',
    borderRight: '1px solid #334155',
    padding: '1.25rem 0',
  },
  sidebarHeader: {
    padding: '0 1rem 1rem',
    borderBottom: '1px solid #334155',
    marginBottom: '0.75rem',
  },
  sidebarTitle: {
    fontSize: '1rem',
    fontWeight: 700,
    margin: 0,
    color: '#f8fafc',
  },
  nav: {
    display: 'flex',
    flexDirection: 'column',
    gap: '0.25rem',
  },
  navItem: {
    display: 'block',
    width: '100%',
    padding: '0.65rem 1rem',
    border: 'none',
    borderLeft: '3px solid transparent',
    background: 'transparent',
    color: '#94a3b8',
    fontSize: '0.95rem',
    textAlign: 'left',
    cursor: 'pointer',
    fontWeight: 500,
  },
  navItemActive: {
    background: '#334155',
    color: '#e2e8f0',
    borderLeftColor: '#3b82f6',
  },
  main: {
    flex: 1,
    maxWidth: 960,
    padding: '2rem 1.5rem',
    overflow: 'auto',
  },
  header: {
    marginBottom: '1.5rem',
  },
  title: {
    fontSize: '1.5rem',
    fontWeight: 700,
    margin: 0,
    color: '#f8fafc',
  },
  subtitle: {
    margin: '0.35rem 0 0',
    color: '#94a3b8',
    fontSize: '0.9rem',
  },
  section: {
    marginBottom: '2rem',
  },
  sectionTitle: {
    fontSize: '1rem',
    fontWeight: 600,
    marginBottom: '0.75rem',
    color: '#e2e8f0',
  },
  uploadRow: {
    display: 'flex',
    flexWrap: 'wrap',
    gap: '1.5rem',
  },
  optionalRow: {
    display: 'flex',
    flexWrap: 'wrap',
    gap: '1.5rem',
    marginTop: '1rem',
  },
  textInput: {
    padding: '0.5rem',
    borderRadius: 8,
    border: '1px solid #334155',
    background: '#1e293b',
    color: '#e2e8f0',
    minWidth: 180,
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
  compareResult: {
    marginTop: '1rem',
  },
  compareGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))',
    gap: '1rem',
    marginTop: '0.75rem',
  },
  compareCol: {
    border: '1px solid #334155',
    borderRadius: 8,
    padding: '0.75rem',
    background: '#1e293b',
  },
  compareColTitle: {
    fontSize: '0.9rem',
    fontWeight: 600,
    margin: '0 0 0.5rem',
    color: '#e2e8f0',
  },
  compareList: {
    margin: 0,
    paddingLeft: '1.25rem',
    fontSize: '0.8rem',
    color: '#94a3b8',
    maxHeight: 200,
    overflowY: 'auto',
  },
  compareLi: {
    marginBottom: '0.25rem',
    wordBreak: 'break-all',
  },
}
