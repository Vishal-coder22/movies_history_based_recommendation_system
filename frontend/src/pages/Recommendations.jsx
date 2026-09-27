import { useState } from 'react'
import {
  Button,
  Card,
  EmptyState,
  ErrorBanner,
  PageHeader,
  Spinner,
} from '../components/ui'
import api, { errorMessage } from '../services/api'

function RecommendationCard({ movie, onDetails }) {
  return (
    <Card className="flex flex-col">
      <div className="flex items-start justify-between gap-3">
        <h3 className="font-medium text-slate-100">{movie.title}</h3>
        <span className="shrink-0 text-sm text-amber-400">
          ★ {movie.vote_average ?? '—'}
        </span>
      </div>
      <p className="mt-0.5 text-xs text-slate-500">{movie.release_year || '—'}</p>
      <p className="mt-2 text-xs text-slate-400">
        {(movie.genre_list || []).join(' · ') || 'No genres'}
      </p>

      <div className="mt-3 flex-1">
        <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
          Why this was recommended
        </p>
        <ul className="mt-1.5 space-y-1">
          {(movie.reasons || [movie.reason]).map((reason) => (
            <li key={reason} className="text-sm text-slate-300">
              {reason}
            </li>
          ))}
        </ul>
      </div>

      <Button variant="secondary" className="mt-4 self-start" onClick={onDetails}>
        View Details
      </Button>
    </Card>
  )
}

export default function Recommendations() {
  const [data, setData] = useState(null)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [details, setDetails] = useState(null)
  const [detailsBusy, setDetailsBusy] = useState(false)

  const generate = async () => {
    setBusy(true)
    setError('')
    setDetails(null)
    try {
      const { data: result } = await api.get('/recommendations', {
        params: { limit: 12 },
      })
      setData(result)
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      setBusy(false)
    }
  }

  const showDetails = async (movie) => {
    setDetailsBusy(true)
    setError('')
    try {
      const { data: result } = await api.get(`/recommendations/${movie.movie_id}`)
      setDetails(result)
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      setDetailsBusy(false)
    }
  }

  return (
    <div>
      <PageHeader
        title="Recommendations"
        subtitle="Built from your watched list, the catalogue's genre patterns and audience ratings."
      />
      <ErrorBanner>{error}</ErrorBanner>

      <Button onClick={generate} disabled={busy}>
        {busy ? 'Generating recommendations…' : data ? 'Refresh recommendations' : 'Generate recommendations'}
      </Button>

      {busy && (
        <div className="mt-4">
          <Spinner label="Generating recommendations…" />
        </div>
      )}

      {detailsBusy && (
        <div className="mt-4">
          <Spinner label="Loading details…" />
        </div>
      )}

      {details && !detailsBusy && (
        <Card className="mt-4 border-amber-900/60">
          <div className="flex items-start justify-between gap-3">
            <div>
              <h2 className="text-lg font-medium text-slate-100">{details.title}</h2>
              <p className="mt-1 text-sm text-slate-400">
                {(details.genre_list || []).join(' · ')} · ★ {details.vote_average ?? '—'}
              </p>
            </div>
            <span className="text-sm text-slate-500">
              match score {details.score}
            </span>
          </div>
          <p className="mt-3 text-sm text-slate-300">{details.reason}</p>
          {details.is_watched && (
            <p className="mt-2 text-xs text-slate-500">
              This movie is already in your watched list.
            </p>
          )}
        </Card>
      )}

      {data && !busy && (
        <div className="mt-4">
          {data.message ? (
            <EmptyState>{data.message}</EmptyState>
          ) : (
            <>
              <p className="mb-3 text-sm text-slate-500">
                Showing {data.items.length} of {data.total} candidates
              </p>
              <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                {data.items.map((movie) => (
                  <RecommendationCard
                    key={movie.movie_id}
                    movie={movie}
                    onDetails={() => showDetails(movie)}
                  />
                ))}
              </div>
            </>
          )}
        </div>
      )}

      {!data && !busy && (
        <div className="mt-4">
          <EmptyState>
            Generate recommendations to see movies matched to your taste.
          </EmptyState>
        </div>
      )}
    </div>
  )
}
