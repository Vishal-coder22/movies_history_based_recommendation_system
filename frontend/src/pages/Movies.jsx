import { useCallback, useEffect, useRef, useState } from 'react'
import {
  Button,
  Card,
  EmptyState,
  ErrorBanner,
  PageHeader,
  Spinner,
} from '../components/ui'
import api, { errorMessage } from '../services/api'

function MovieCard({ movie, onAdd }) {
  const [rating, setRating] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  const add = async () => {
    const trimmed = rating.trim()
    if (trimmed !== '') {
      const value = Number(trimmed)
      if (Number.isNaN(value) || value < 0 || value > 5) {
        setError('Your rating must be between 0 and 5.')
        return
      }
    }
    setBusy(true)
    setError('')
    try {
      await api.post(`/movies/${movie.movie_id}/watched`, {
        rating: trimmed === '' ? null : Number(trimmed),
      })
      onAdd(movie)
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      setBusy(false)
    }
  }

  return (
    <Card className="flex flex-col">
      <div className="flex-1">
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
      </div>

      {movie.is_watched ? (
        <p className="mt-3 rounded-md border border-slate-700 px-3 py-1.5 text-center text-xs text-slate-400">
          In your watched list
          {movie.user_rating != null && ` · you rated ${movie.user_rating}★`}
        </p>
      ) : (
        <div className="mt-3">
          <label htmlFor={`rating-${movie.movie_id}`} className="sr-only">
            Your rating for {movie.title}
          </label>
          <div className="flex gap-2">
            <input
              id={`rating-${movie.movie_id}`}
              type="number"
              min="0"
              max="5"
              step="0.5"
              value={rating}
              onChange={(event) => setRating(event.target.value)}
              placeholder="Rating (0–5)"
              className="w-full rounded-md border border-slate-700 bg-slate-950 px-2 py-1.5 text-sm text-slate-100 outline-none focus:border-amber-500"
            />
            <Button onClick={add} disabled={busy} className="shrink-0">
              {busy ? '…' : 'Add'}
            </Button>
          </div>
          {error && <p className="mt-1 text-xs text-rose-400">{error}</p>}
        </div>
      )}
    </Card>
  )
}

export default function Movies() {
  const [query, setQuery] = useState('')
  const [genre, setGenre] = useState('')
  const [minRating, setMinRating] = useState('')
  const [items, setItems] = useState([])
  const [total, setTotal] = useState(0)
  const [genres, setGenres] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const timer = useRef(null)

  useEffect(() => {
    api
      .get('/movies/genres')
      .then(({ data }) => setGenres(data.genres))
      .catch(() => {})
  }, [])

  const fetchMovies = useCallback(
    (overrides = {}) => {
      const params = {
        q: query.trim() || undefined,
        genre: genre || undefined,
        min_rating: minRating ? Number(minRating) : undefined,
        limit: 24,
        ...overrides,
      }
      setLoading(true)
      setError('')
      api
        .get('/movies', { params })
        .then(({ data }) => {
          setItems(data.items)
          setTotal(data.total)
        })
        .catch((err) => setError(errorMessage(err)))
        .finally(() => setLoading(false))
    },
    [query, genre, minRating],
  )

  useEffect(() => {
    if (timer.current) clearTimeout(timer.current)
    timer.current = setTimeout(() => fetchMovies(), 300)
    return () => timer.current && clearTimeout(timer.current)
  }, [fetchMovies])

  const handleAdded = (movie) => {
    setNotice(`${movie.title} added to your watched list.`)
    setItems((prev) =>
      prev.map((item) =>
        item.movie_id === movie.movie_id
          ? { ...item, is_watched: true }
          : item,
      ),
    )
  }

  return (
    <div>
      <PageHeader
        title="Movies"
        subtitle="Search the master catalogue and track what you have watched."
      />
      <ErrorBanner>{error}</ErrorBanner>
      {notice && (
        <div className="mb-4 rounded-lg border border-emerald-800 bg-emerald-950/50 px-4 py-3 text-sm text-emerald-200">
          {notice}
        </div>
      )}

      <Card>
        <div className="grid gap-3 md:grid-cols-3">
          <div>
            <label htmlFor="movie-search" className="block text-sm font-medium text-slate-300">
              Search
            </label>
            <input
              id="movie-search"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Search movies…"
              className="mt-1 w-full rounded-md border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-100 outline-none focus:border-amber-500"
            />
          </div>
          <div>
            <label htmlFor="genre-filter" className="block text-sm font-medium text-slate-300">
              Genre
            </label>
            <select
              id="genre-filter"
              value={genre}
              onChange={(event) => setGenre(event.target.value)}
              className="mt-1 w-full rounded-md border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-100 outline-none focus:border-amber-500"
            >
              <option value="">All</option>
              {genres.map((name) => (
                <option key={name} value={name}>
                  {name}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label htmlFor="min-rating" className="block text-sm font-medium text-slate-300">
              Minimum rating
            </label>
            <input
              id="min-rating"
              type="number"
              min="0"
              max="10"
              step="0.5"
              value={minRating}
              onChange={(event) => setMinRating(event.target.value)}
              placeholder="0"
              className="mt-1 w-full rounded-md border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-100 outline-none focus:border-amber-500"
            />
          </div>
        </div>
        <p className="mt-3 text-xs text-slate-500">
          Showing {items.length} of {total} movies
        </p>
      </Card>

      {loading ? (
        <div className="mt-4">
          <Spinner label="Searching movies…" />
        </div>
      ) : items.length === 0 ? (
        <div className="mt-4">
          <EmptyState>No movies match those filters. Try a different search.</EmptyState>
        </div>
      ) : (
        <div className="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {items.map((movie) => (
            <MovieCard key={movie.movie_id} movie={movie} onAdd={handleAdded} />
          ))}
        </div>
      )}
    </div>
  )
}
