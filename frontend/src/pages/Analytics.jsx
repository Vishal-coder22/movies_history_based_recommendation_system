import { useEffect, useState } from 'react'
import { GenreChart } from '../components/GenreChart'
import { RatingChart } from '../components/RatingChart'
import {
  Card,
  EmptyState,
  ErrorBanner,
  PageHeader,
  Spinner,
  SummaryCard,
} from '../components/ui'
import api, { errorMessage } from '../services/api'

export default function Analytics() {
  const [summary, setSummary] = useState(null)
  const [genres, setGenres] = useState(null)
  const [ratings, setRatings] = useState(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let cancelled = false
    Promise.all([
      api.get('/analytics/summary'),
      api.get('/analytics/genres'),
      api.get('/analytics/ratings'),
    ])
      .then(([s, g, r]) => {
        if (cancelled) return
        setSummary(s.data)
        setGenres(g.data)
        setRatings(r.data)
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
  }, [])

  if (loading) return <Spinner label="Loading analytics…" />
  if (error) return <ErrorBanner>{error}</ErrorBanner>
  if (!summary) return null

  if (summary.movies_watched === 0) {
    return (
      <div>
        <PageHeader title="Analytics" />
        <EmptyState>Upload your movie history to see your analytics.</EmptyState>
      </div>
    )
  }

  const genreCount = Object.keys(summary.genre_counts || {}).length
  const pieData = Object.entries(summary.genre_counts || {}).map(([name, value]) => ({
    name,
    value,
  }))
  const ratingData = (ratings?.distribution || []).map((row) => ({
    label: `${row.rating}★`,
    value: row.count,
  }))
  const genreAvgData = (genres?.genres || [])
    .filter((row) => row.average_rating !== null)
    .map((row) => ({ label: row.genre, value: row.average_rating }))

  return (
    <div>
      <PageHeader
        title="Analytics"
        subtitle="How your watched history breaks down."
      />

      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        <SummaryCard label="Movies Watched" value={summary.movies_watched} />
        <SummaryCard
          label="Average Rating"
          value={summary.average_rating ?? '—'}
          hint={`${summary.rated_count} rated`}
        />
        <SummaryCard label="Genres" value={genreCount} />
        <SummaryCard label="Most Represented" value={summary.most_common_genre ?? '—'} />
      </div>

      <div className="mt-6 grid gap-4 lg:grid-cols-2">
        <Card>
          <GenreChart data={pieData} />
        </Card>
        <Card>
          <RatingChart data={ratingData} title="Rating distribution" yLabel="Movies" />
          {ratingData.length === 0 && (
            <p className="text-sm text-slate-500">
              Add a personal rating to a movie to see this chart.
            </p>
          )}
        </Card>
        <Card className="lg:col-span-2">
          <RatingChart
            data={genreAvgData}
            title="Genre vs average rating"
            yLabel="Rating"
          />
          {genreAvgData.length === 0 && (
            <p className="text-sm text-slate-500">
              Rate a few movies to compare genres by your average rating.
            </p>
          )}
        </Card>
      </div>
    </div>
  )
}
