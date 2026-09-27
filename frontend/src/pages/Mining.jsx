import { useEffect, useState } from 'react'
import {
  ClusterCard,
  ProbabilityList,
  RuleTable,
} from '../components/MiningCards'
import {
  Button,
  Card,
  EmptyState,
  ErrorBanner,
  PageHeader,
  Spinner,
} from '../components/ui'
import api, { errorMessage } from '../services/api'

const TABS = [
  { id: 'kmeans', label: 'K-Means' },
  { id: 'apriori', label: 'Apriori' },
  { id: 'naive_bayes', label: 'Naive Bayes' },
]

function Field({ id, label, hint, ...props }) {
  return (
    <div>
      <label htmlFor={id} className="block text-sm font-medium text-slate-300">
        {label}
      </label>
      <input
        id={id}
        className="mt-1 w-32 rounded-md border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-100 outline-none focus:border-amber-500"
        {...props}
      />
      {hint && <p className="mt-1 text-xs text-slate-500">{hint}</p>}
    </div>
  )
}

export default function Mining() {
  const [tab, setTab] = useState('kmeans')
  const [k, setK] = useState('3')
  const [minSupport, setMinSupport] = useState('0.1')
  const [minConfidence, setMinConfidence] = useState('0.3')
  const [results, setResults] = useState({})
  const [error, setError] = useState('')
  const [busy, setBusy] = useState('')
  const [runs, setRuns] = useState([])

  useEffect(() => {
    api
      .get('/mining/runs')
      .then(({ data }) => setRuns(data.runs))
      .catch(() => {})
  }, [])

  const recordRun = (data) => {
    setRuns((prev) => [
      {
        run_id: data.run_id,
        algorithm: tab,
        created_at: new Date().toISOString(),
        metrics: {},
      },
      ...prev,
    ])
  }

  const run = async () => {
    setBusy(tab)
    setError('')
    try {
      if (tab === 'kmeans') {
        const parsedK = Number(k)
        if (!Number.isInteger(parsedK) || parsedK < 2 || parsedK > 6) {
          throw { response: { data: { detail: 'Choose a cluster count (K) between 2 and 6.' } } }
        }
        const { data } = await api.post('/mining/kmeans', { k: parsedK })
        setResults((prev) => ({ ...prev, kmeans: data }))
        recordRun(data)
      } else if (tab === 'apriori') {
        const { data } = await api.post('/mining/apriori', {
          min_support: Number(minSupport),
          min_confidence: Number(minConfidence),
        })
        setResults((prev) => ({ ...prev, apriori: data }))
        recordRun(data)
      } else {
        const { data } = await api.post('/mining/naive-bayes')
        setResults((prev) => ({ ...prev, naive_bayes: data }))
        recordRun(data)
      }
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      setBusy('')
    }
  }

  const busyLabel = {
    kmeans: 'Running K-Means…',
    apriori: 'Generating association rules…',
    naive_bayes: 'Training Naive Bayes…',
  }

  return (
    <div>
      <PageHeader
        title="Mining"
        subtitle="Three data-mining views over your history. The backend does the maths — this page just shows it."
      />
      <ErrorBanner>{error}</ErrorBanner>

      <div className="flex gap-2 border-b border-slate-800" role="tablist">
        {TABS.map((item) => (
          <button
            key={item.id}
            role="tab"
            aria-selected={tab === item.id}
            onClick={() => {
              setTab(item.id)
              setError('')
            }}
            className={`-mb-px border-b-2 px-4 py-2 text-sm transition-colors ${
              tab === item.id
                ? 'border-amber-500 font-medium text-amber-400'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            {item.label}
          </button>
        ))}
      </div>

      <Card className="mt-4">
        {tab === 'kmeans' && (
          <div className="flex flex-wrap items-end gap-4">
            <Field
              id="k-value"
              label="Clusters (K)"
              hint="Between 2 and 6"
              type="number"
              min="2"
              max="6"
              value={k}
              onChange={(event) => setK(event.target.value)}
            />
            <Button onClick={run} disabled={busy === 'kmeans'}>
              {busy === 'kmeans' ? 'Running…' : 'Run K-Means'}
            </Button>
          </div>
        )}

        {tab === 'apriori' && (
          <div className="flex flex-wrap items-end gap-4">
            <Field
              id="min-support"
              label="Minimum support"
              hint="0–1, e.g. 0.1 = 10%"
              type="number"
              step="0.05"
              min="0.01"
              max="1"
              value={minSupport}
              onChange={(event) => setMinSupport(event.target.value)}
            />
            <Field
              id="min-confidence"
              label="Minimum confidence"
              hint="0–1, e.g. 0.3 = 30%"
              type="number"
              step="0.05"
              min="0.01"
              max="1"
              value={minConfidence}
              onChange={(event) => setMinConfidence(event.target.value)}
            />
            <Button onClick={run} disabled={busy === 'apriori'}>
              {busy === 'apriori' ? 'Generating…' : 'Run Apriori'}
            </Button>
          </div>
        )}

        {tab === 'naive_bayes' && (
          <div className="flex flex-wrap items-end gap-4">
            <p className="max-w-md text-sm text-slate-400">
              Trains one genre classifier per genre on the catalogue, then predicts how much
              your watched profile matches each genre.
            </p>
            <Button onClick={run} disabled={busy === 'naive_bayes'}>
              {busy === 'naive_bayes' ? 'Training…' : 'Run Naive Bayes'}
            </Button>
          </div>
        )}
      </Card>

      {busy && (
        <div className="mt-4">
          <Spinner label={busyLabel[busy]} />
        </div>
      )}

      {tab === 'kmeans' && results.kmeans && !busy && (
        <div className="mt-4">
          <Card>
            <p className="text-sm text-slate-400">
              <span className="text-slate-200">{results.kmeans.movie_count}</span> watched
              movies grouped into{' '}
              <span className="text-slate-200">{results.kmeans.profiles.length}</span> clusters
              (K = {results.kmeans.k}) · silhouette score{' '}
              <span className="text-slate-200">{results.kmeans.silhouette_score}</span>
            </p>
          </Card>
          <div className="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {results.kmeans.profiles.map((profile, index) => (
              <ClusterCard key={profile.cluster_id} profile={profile} index={index} />
            ))}
          </div>
        </div>
      )}

      {tab === 'apriori' && results.apriori && !busy && (
        <Card className="mt-4">
          <p className="text-sm text-slate-400">
            {results.apriori.transaction_count} catalogue movies as transactions ·{' '}
            {results.apriori.frequent_itemset_count} frequent itemsets ·{' '}
            {results.apriori.rules.length} rules
          </p>
          {results.apriori.message ? (
            <p className="mt-3 text-sm text-slate-300">{results.apriori.message}</p>
          ) : (
            <div className="mt-4">
              <RuleTable rules={results.apriori.rules} />
            </div>
          )}
        </Card>
      )}

      {tab === 'naive_bayes' && results.naive_bayes && !busy && (
        <div className="mt-4 grid gap-4 lg:grid-cols-2">
          <Card>
            <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
              Model predictions for your profile
            </p>
            <p className="mt-1 text-sm text-slate-400">
              Based on {results.naive_bayes.user_movies} watched movies ·{' '}
              {results.naive_bayes.modelled_genres} genres modelled from{' '}
              {results.naive_bayes.trained_movies} catalogue movies
            </p>
            <div className="mt-4">
              <ProbabilityList probabilities={results.naive_bayes.probabilities} />
            </div>
          </Card>
          <Card>
            <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
              Holdout accuracy by genre
            </p>
            <div className="mt-3 overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead>
                  <tr className="border-b border-slate-700 text-slate-400">
                    <th className="py-2 pr-3 font-medium">Genre</th>
                    <th className="py-2 pr-3 text-right font-medium">Accuracy</th>
                    <th className="py-2 pr-3 text-right font-medium">F1</th>
                    <th className="py-2 text-right font-medium">Holdout</th>
                  </tr>
                </thead>
                <tbody>
                  {results.naive_bayes.metrics.map((row) => (
                    <tr
                      key={row.genre}
                      className="border-b border-slate-800/70 last:border-0"
                    >
                      <td className="py-2 pr-3 text-slate-200">{row.genre}</td>
                      <td className="py-2 pr-3 text-right text-slate-300">
                        {(row.accuracy * 100).toFixed(0)}%
                      </td>
                      <td className="py-2 pr-3 text-right text-slate-300">
                        {(row.f1 * 100).toFixed(0)}%
                      </td>
                      <td className="py-2 text-right text-slate-400">
                        {row.holdout_size} movies
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>
        </div>
      )}

      {runs.length > 0 && (
        <Card className="mt-6">
          <h2 className="text-sm font-medium uppercase tracking-wide text-slate-500">
            Run history
          </h2>
          <ul className="mt-3 space-y-2">
            {runs.slice(0, 8).map((item) => (
              <li
                key={item.run_id}
                className="flex items-center justify-between border-b border-slate-800/70 pb-2 text-sm last:border-0 last:pb-0"
              >
                <span className="text-slate-300">
                  {TABS.find((t) => t.id === item.algorithm)?.label || item.algorithm}
                </span>
                <span className="text-xs text-slate-500">
                  {new Date(item.created_at).toLocaleString()}
                </span>
              </li>
            ))}
          </ul>
        </Card>
      )}

      {!busy && !results[tab] && runs.length === 0 && (
        <div className="mt-4">
          <EmptyState>
            Add at least several movies before running mining analysis.
          </EmptyState>
        </div>
      )}
    </div>
  )
}
