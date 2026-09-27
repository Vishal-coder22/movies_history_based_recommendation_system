import { useEffect, useState } from 'react'
import { GenreChart } from '../components/GenreChart'
import { RatingChart } from '../components/RatingChart'
import { Card, EmptyState, ErrorBanner, PageHeader, Spinner, SummaryCard } from '../components/ui'
import api, { errorMessage } from '../services/api'

export default function Dashboard() {
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

  if (loading) return <Spinner label="Loading your dashboard…" />
  if (error) return <ErrorBanner>{error}</ErrorBanner>
  if (!summary) return null

  const quality = summary.data_quality || {}
  const genreEntries = Object.entries(summary.genre_counts || {})
  const pieData = genreEntries.map(([name, value]) => ({ name, value }))
  const ratingData = (ratings?.distribution || []).map((row) => ({
    label: `${row.rating}★`,
    value: row.count,
  }))
  const genreAvgData = (genres?.genres || [])
    .filter((row) => row.average_rating !== null)
    .map((row) => ({ label: row.genre, value: row.average_rating }))

  const topGenre = genreEntries.slice().sort((a, b) => b[1] - a[1])[0]
  const topShare = topGenre && summary.total_genre_assignments
    ? Math.round((topGenre[1] / summary.total_genre_assignments) * 100)
    : 0

  const insights = []
  if (topGenre && summary.movies_watched > 0) {
    insights.push(
      `${topGenre[0]} represents ${topShare}% of your watched movies.`,
    )
  }
  if (summary.unique_watched) {
    insights.push(`You have watched ${summary.unique_watched} unique movies.`)
  }
  if (quality.duplicates_removed) {
    insights.push(
      `${quality.duplicates_removed} duplicate record${quality.duplicates_removed === 1 ? ' was' : 's were'} removed during preprocessing.`,
    )
  }
  if (quality.missing_values) {
    insights.push(
      `${quality.missing_values} record${quality.missing_values === 1 ? ' had' : 's had'} a missing movie name and ${quality.missing_values === 1 ? 'was' : 'were'} skipped.`,
    )
  }

  return (
    <div>
      <PageHeader title="Dashboard" subtitle="A snapshot of your movie history." />

      {summary.movies_watched === 0 ? (
        <EmptyState>
          Upload your movie history to see your analytics.
        </EmptyState>
      ) : (
        <>
          <div className="grid grid-cols-2 gap-4 md:grid-cols-3 lg:grid-cols-6">
            <SummaryCard label="Movies Watched" value={summary.movies_watched} />
            <SummaryCard
              label="Average Rating"
              value={summary.average_rating ?? '—'}
              hint={summary.rated_count ? `from ${summary.rated_count} ratings` : 'no ratings yet'}
            />
            <SummaryCard label="Top Genre" value={summary.most_common_genre ?? '—'} />
            <SummaryCard label="Unique Genres" value={Object.keys(summary.genre_counts || {}).length} />
            <SummaryCard label="Duplicates Removed" value={quality.duplicates_removed ?? 0} />
            <SummaryCard label="Missing Values" value={quality.missing_values ?? 0} />
          </div>

          <div className="mt-6 grid gap-4 lg:grid-cols-3">
            <Card>
              <GenreChart data={pieData} />
            </Card>
            <Card>
              <RatingChart
                data={ratingData}
                title="Rating distribution"
                yLabel="Movies"
              />
              {ratingData.length === 0 && (
                <p className="text-sm text-slate-500">
                  Add a personal rating to a movie to see this chart.
                </p>
              )}
            </Card>
            <Card>
              <RatingChart
                data={genreAvgData}
                title="Genre vs average rating"
                yLabel="Rating"
              />
            </Card>
          </div>

          {insights.length > 0 && (
            <div className="mt-6 grid gap-4 md:grid-cols-3">
              {insights.map((text) => (
                <Card key={text} className="border-slate-800 bg-slate-900/60">
                  <p className="text-sm text-slate-300">{text}</p>
                </Card>
              ))}
            </div>
          )}
        </>
      )}
    </div>
  )
}
