import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Button, Card, ErrorBanner, PageHeader, Spinner } from '../components/ui'
import api, { errorMessage } from '../services/api'

const PROCESSING_LABEL = {
  csv: 'Processing…',
  pdf: 'Extracting PDF table…',
}

export default function Upload() {
  const navigate = useNavigate()
  const [preview, setPreview] = useState(null)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [busyKind, setBusyKind] = useState('csv')

  const handleFile = async (kind) => async (event) => {
    const file = event.target.files?.[0]
    event.target.value = ''
    if (!file) return

    setError('')
    setPreview(null)
    setBusy(true)
    setBusyKind(kind)

    const body = new FormData()
    body.append('file', file)
    try {
      const { data } = await api.post(`/upload/${kind}`, body, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      setPreview(data)
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      setBusy(false)
    }
  }

  const dropId = (kind) => `upload-${kind}`

  return (
    <div>
      <PageHeader
        title="Upload"
        subtitle="Upload your movie history as a CSV or PDF file."
      />
      <ErrorBanner>{error}</ErrorBanner>

      {!preview && (
        <div className="grid gap-4 md:grid-cols-2">
          <Card>
            <h2 className="text-lg font-medium text-slate-100">Upload CSV</h2>
            <p className="mt-2 text-sm text-slate-400">
              Accepted format: UTF-8 CSV with a <code className="text-slate-300">Movie</code>{' '}
              column and an optional <code className="text-slate-300">Rating</code> column.
              Maximum file size: 10 MB.
            </p>
            <label
              htmlFor={dropId('csv')}
              className="mt-4 inline-block cursor-pointer rounded-md bg-amber-500 px-4 py-2 text-sm font-medium text-slate-950 transition-colors hover:bg-amber-400"
            >
              Choose File
            </label>
            <input
              id={dropId('csv')}
              type="file"
              accept=".csv,text/csv"
              className="sr-only"
              onChange={handleFile('csv')}
              disabled={busy}
            />
          </Card>

          <Card>
            <h2 className="text-lg font-medium text-slate-100">Upload PDF</h2>
            <p className="mt-2 text-sm text-slate-400">
              Expected format: a PDF containing a table with a{' '}
              <code className="text-slate-300">Movie</code> column and an optional{' '}
              <code className="text-slate-300">Rating</code> column. Maximum file size: 10 MB.
            </p>
            <label
              htmlFor={dropId('pdf')}
              className="mt-4 inline-block cursor-pointer rounded-md bg-amber-500 px-4 py-2 text-sm font-medium text-slate-950 transition-colors hover:bg-amber-400"
            >
              Choose File
            </label>
            <input
              id={dropId('pdf')}
              type="file"
              accept=".pdf,application/pdf"
              className="sr-only"
              onChange={handleFile('pdf')}
              disabled={busy}
            />
          </Card>
        </div>
      )}

      {busy && (
        <div className="mt-6">
          <Spinner label={PROCESSING_LABEL[busyKind]} />
        </div>
      )}

      {preview && !busy && (
        <Card className="mt-2">
          <h2 className="text-lg font-medium text-slate-100">Preview</h2>

          <dl className="mt-4 grid grid-cols-2 gap-x-6 gap-y-2 text-sm md:grid-cols-3">
            <div>
              <dt className="text-slate-500">File</dt>
              <dd className="text-slate-200">{preview.file_name}</dd>
            </div>
            <div>
              <dt className="text-slate-500">File type</dt>
              <dd className="uppercase text-slate-200">{preview.file_type}</dd>
            </div>
            <div>
              <dt className="text-slate-500">Rows detected</dt>
              <dd className="text-slate-200">{preview.total_rows}</dd>
            </div>
          </dl>

          <div className="mt-4">
            <p className="text-sm font-medium text-slate-500">Columns</p>
            <div className="mt-1 flex flex-wrap gap-2">
              {['movie', 'rating', 'movie_id']
                .filter((key) => preview.columns?.[key])
                .map((key) => (
                  <span
                    key={key}
                    className="rounded-full border border-slate-700 px-3 py-1 text-xs text-slate-300"
                  >
                    {preview.columns[key]}
                  </span>
                ))}
              {Object.keys(preview.columns || {}).length === 0 && (
                <span className="text-sm text-slate-500">No named columns detected.</span>
              )}
            </div>
          </div>

          {preview.warnings?.length > 0 && (
            <ul className="mt-4 space-y-1 rounded-lg border border-amber-800 bg-amber-950/40 px-4 py-3 text-sm text-amber-200">
              {preview.warnings.map((warning) => (
                <li key={warning}>{warning}</li>
              ))}
            </ul>
          )}

          <div className="mt-4 overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-slate-800 text-slate-500">
                  <th className="py-2 pr-4 font-medium">#</th>
                  <th className="py-2 pr-4 font-medium">Movie</th>
                  <th className="py-2 font-medium">Rating</th>
                </tr>
              </thead>
              <tbody>
                {preview.sample_rows.map((row, index) => (
                  <tr key={row.record_id} className="border-b border-slate-800/60">
                    <td className="py-2 pr-4 text-slate-500">{index + 1}</td>
                    <td className="py-2 pr-4 text-slate-200">
                      {row.raw_movie_title || (
                        <span className="text-slate-600">(empty)</span>
                      )}
                    </td>
                    <td className="py-2 text-slate-300">
                      {row.raw_rating || <span className="text-slate-600">—</span>}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="mt-5 flex gap-3">
            <Button onClick={() => navigate(`/cleaning/${preview.import_id}`)}>
              Continue
            </Button>
            <Button variant="ghost" onClick={() => setPreview(null)}>
              Upload another file
            </Button>
          </div>
        </Card>
      )}
    </div>
  )
}
