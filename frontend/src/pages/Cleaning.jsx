import { useCallback, useEffect, useRef, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import {
  Button,
  Card,
  EmptyState,
  ErrorBanner,
  PageHeader,
  Spinner,
} from '../components/ui'
import api, { errorMessage } from '../services/api'

const REPORT_ROWS = [
  ['original_rows', 'Original records', 'Every row read from your file.'],
  ['duplicate_rows', 'Duplicates', 'The same movie record appeared more than once.'],
  ['missing_movie_rows', 'Missing movie names', 'Required information was empty.'],
  ['invalid_rows', 'Invalid records', 'A value could not be used (for example a rating outside 0–5).'],
  ['matched_rows', 'Matched', 'Found confidently in the master catalogue.'],
  ['ambiguous_rows', 'Ambiguous', 'Multiple movies were possible matches.'],
  ['unmatched_rows', 'Unmatched', 'Could not be confidently found in the master catalogue.'],
  ['final_rows', 'Final rows', 'Records ready to import.'],
]

function MatchReview({ record, selected, touched, onChange }) {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState([])
  const [searching, setSearching] = useState(false)
  const timer = useRef(null)

  const isAmbiguous = Array.isArray(record.candidates) && record.candidates.length > 0

  const runSearch = useCallback((term) => {
    api
      .get('/movies', { params: { q: term, limit: 5 } })
      .then(({ data }) => setResults(data.items))
      .catch(() => setResults([]))
      .finally(() => setSearching(false))
  }, [])

  const handleSearch = (event) => {
    const term = event.target.value
    setQuery(term)
    if (timer.current) clearTimeout(timer.current)
    if (term.trim().length < 2) {
      setResults([])
      return
    }
    setSearching(true)
    timer.current = setTimeout(() => runSearch(term.trim()), 300)
  }

  useEffect(() => () => timer.current && clearTimeout(timer.current), [])

  const options = isAmbiguous
    ? record.candidates.map((candidate) => ({
        movie_id: candidate.movie_id,
        label: `${candidate.title}${candidate.release_year ? ` (${candidate.release_year})` : ''}`,
        hint: candidate.score ? `match ${Math.round(candidate.score * 100)}%` : '',
      }))
    : results.map((movie) => ({
        movie_id: movie.movie_id,
        label: `${movie.title}${movie.release_year ? ` (${movie.release_year})` : ''}`,
        hint: (movie.genre_list || []).slice(0, 3).join(' · '),
      }))

  return (
    <div className="rounded-lg border border-slate-800 bg-slate-950/60 p-4">
      <p className="text-sm text-slate-500">Uploaded title</p>
      <p className="font-medium text-slate-100">{record.raw_movie_title || '(empty)'}</p>

      {isAmbiguous ? (
        <fieldset className="mt-3">
          <legend className="text-sm text-slate-400">Possible matches</legend>
          <div className="mt-2 space-y-1">
            {options.map((option) => (
              <label
                key={option.movie_id}
                className={`flex cursor-pointer items-center gap-3 rounded-md border px-3 py-2 text-sm transition-colors ${
                  value === option.movie_id
                    ? 'border-amber-600 bg-amber-950/40 text-slate-100'
                    : 'border-slate-800 text-slate-300 hover:border-slate-600'
                }`}
              >
                <input
                  type="radio"
                  name={`record-${record.record_id}`}
                  checked={touched && selected === option.movie_id}
                  onChange={() => onChange(option.movie_id)}
                  className="accent-amber-500"
                />
                <span className="flex-1">{option.label}</span>
                {option.hint && (
                  <span className="text-xs text-slate-500">{option.hint}</span>
                )}
              </label>
            ))}
            <label
              className={`flex cursor-pointer items-center gap-3 rounded-md border px-3 py-2 text-sm ${
                touched && selected === null
                  ? 'border-slate-600 bg-slate-900 text-slate-200'
                  : 'border-slate-800 text-slate-400 hover:border-slate-600'
              }`}
            >
              <input
                type="radio"
                name={`record-${record.record_id}`}
                checked={touched && selected === null}
                onChange={() => onChange(null)}
                className="accent-amber-500"
              />
              Skip this record
            </label>
          </div>
        </fieldset>
      ) : (
        <div className="mt-3">
          <label
            htmlFor={`search-${record.record_id}`}
            className="block text-sm text-slate-400"
          >
            Search the catalogue for the right movie
          </label>
          <input
            id={`search-${record.record_id}`}
            value={query}
            onChange={handleSearch}
            placeholder="Search movies…"
            className="mt-2 w-full rounded-md border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-100 outline-none focus:border-amber-500"
          />
          {searching && <p className="mt-2 text-xs text-slate-500">Searching…</p>}
          <div className="mt-2 space-y-1">
            {options.map((option) => (
              <label
                key={option.movie_id}
                className={`flex cursor-pointer items-center gap-3 rounded-md border px-3 py-2 text-sm ${
                  touched && selected === option.movie_id
                    ? 'border-amber-600 bg-amber-950/40 text-slate-100'
                    : 'border-slate-800 text-slate-300 hover:border-slate-600'
                }`}
              >
                <input
                  type="radio"
                  name={`record-${record.record_id}`}
                  checked={touched && selected === option.movie_id}
                  onChange={() => onChange(option.movie_id)}
                  className="accent-amber-500"
                />
                <span className="flex-1">{option.label}</span>
                {option.hint && (
                  <span className="text-xs text-slate-500">{option.hint}</span>
                )}
              </label>
            ))}
            {touched && selected === null && (
              <p className="text-xs text-slate-500">
                Skip selected — this record will not be imported.
              </p>
            )}
            <button
              type="button"
              onClick={() => onChange(null)}
              className="text-xs text-slate-500 underline hover:text-slate-300"
            >
              Skip this record
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

export default function Cleaning() {
  const { importId } = useParams()
  const navigate = useNavigate()

  const [preview, setPreview] = useState(null)
  const [result, setResult] = useState(null)
  const [decisions, setDecisions] = useState({})
  const [showReview, setShowReview] = useState(false)
  const [done, setDone] = useState(null)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState('')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let cancelled = false
    api
      .get(`/imports/${importId}`)
      .then(({ data }) => {
        if (!cancelled) setPreview(data)
      })
      .catch((err) => {
        if (!cancelled) setError(errorMessage(err))
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [importId])

  const clean = async () => {
    setBusy('clean')
    setError('')
    try {
      const { data } = await api.post(`/imports/${importId}/clean`)
      setResult(data)
      setDecisions({})
      setShowReview(data.ambiguous.length + data.unmatched.length > 0)
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      setBusy('')
    }
  }

  const confirm = async () => {
    setBusy('confirm')
    setError('')
    try {
      if (result && pendingRecords.length > 0) {
        await api.post(`/imports/${importId}/confirm-matches`, {
          decisions: pendingRecords.map((record) => ({
            record_id: record.record_id,
            movie_id: decisions[record.record_id],
          })),
        })
      }
      const { data } = await api.post(`/imports/${importId}/confirm`)
      setDone(data)
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      setBusy('')
    }
  }

  if (loading) return <Spinner label="Loading this import…" />

  const report = result?.report || preview?.report
  const pendingRecords = result
    ? [...result.ambiguous.map((r) => ({ ...r, kind: 'ambiguous' })),
       ...result.unmatched.map((r) => ({ ...r, kind: 'unmatched' }))]
    : []
  const unresolved = pendingRecords.filter(
    (record) => !(record.record_id in decisions),
  ).length

  if (done) {
    return (
      <div>
        <PageHeader title="Import complete" />
        <Card>
          <p className="text-slate-200">
            {done.inserted} movie{done.inserted === 1 ? '' : 's'} added to your watched list.
          </p>
          {done.already_watched > 0 && (
            <p className="mt-1 text-sm text-slate-400">
              {done.already_watched} record{done.already_watched === 1 ? '' : 's'} were already
              in your list and {done.already_watched === 1 ? 'was' : 'were'} skipped.
            </p>
          )}
          <div className="mt-5 flex gap-3">
            <Button onClick={() => navigate('/')}>
              Go to dashboard
            </Button>
            <Button variant="secondary" onClick={() => navigate('/upload')}>
              Upload another file
            </Button>
          </div>
        </Card>
      </div>
    )
  }

  return (
    <div>
      <PageHeader
        title="Data cleaning review"
        subtitle="Review what was found before importing your history."
      />
      <ErrorBanner>{error}</ErrorBanner>

      {!report && !result && (
        <Card>
          <p className="text-sm text-slate-400">
            {preview?.file_name} is ready — {preview?.total_rows} rows detected. Clean the data
            to detect duplicates, missing values and catalogue matches.
          </p>
          <Button className="mt-4" onClick={clean} disabled={busy === 'clean'}>
            {busy === 'clean' ? 'Cleaning data…' : 'Clean Data'}
          </Button>
        </Card>
      )}

      {report && (
        <Card>
          <table className="w-full text-sm">
            <tbody>
              {REPORT_ROWS.map(([key, label, explanation]) => (
                <tr key={key} className="border-b border-slate-800/70 last:border-0">
                  <td className="w-56 py-2.5 text-slate-300">{label}</td>
                  <td className="w-24 py-2.5 text-right font-medium text-slate-100">
                    {report[key]}
                  </td>
                  <td className="py-2.5 pl-6 text-slate-500">{explanation}</td>
                </tr>
              ))}
            </tbody>
          </table>

          <div className="mt-5 flex flex-wrap gap-3">
            {pendingRecords.length > 0 && (
              <Button variant="secondary" onClick={() => setShowReview((v) => !v)}>
                {showReview ? 'Hide match review' : `Review Matches (${pendingRecords.length})`}
              </Button>
            )}
            {!result && (
              <Button onClick={clean} disabled={busy === 'clean'}>
                {busy === 'clean' ? 'Cleaning data…' : 'Clean Data'}
              </Button>
            )}
            {result && (
              <div>
                <Button onClick={confirm} disabled={busy === 'confirm' || unresolved > 0}>
                  {busy === 'confirm' ? 'Importing…' : 'Add to Watched List'}
                </Button>
                {unresolved > 0 && (
                  <p className="mt-2 text-xs text-slate-500">
                    Choose a movie (or skip) for the {unresolved} remaining record
                    {unresolved === 1 ? '' : 's'} to continue.
                  </p>
                )}
              </div>
            )}
          </div>
        </Card>
      )}

      {showReview && pendingRecords.length > 0 && (
        <Card className="mt-4">
          <h2 className="text-lg font-medium text-slate-100">Match review</h2>
          <p className="mt-1 text-sm text-slate-400">
            Ambiguous records need your choice — CineMine never picks one for you. Unmatched
            records can be searched manually or skipped.
          </p>
          <div className="mt-4 space-y-4">
            {pendingRecords.map((record) => (
              <MatchReview
                key={record.record_id}
                record={record}
                selected={decisions[record.record_id]}
                touched={record.record_id in decisions}
                onChange={(movie_id) =>
                  setDecisions((prev) => ({ ...prev, [record.record_id]: movie_id }))
                }
              />
            ))}
          </div>
        </Card>
      )}

      {report && pendingRecords.length === 0 && !result && (
        <EmptyState>
          No ambiguous or unmatched records — you can import this file directly.
        </EmptyState>
      )}
    </div>
  )
}
