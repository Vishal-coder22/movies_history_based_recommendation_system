import { Card } from './ui'

export function ClusterCard({ profile, index }) {
  return (
    <Card>
      <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
        Cluster {index + 1}
      </p>
      <p className="mt-2 text-lg font-medium text-slate-100">
        {profile.dominant_genre || 'Mixed genres'}
      </p>
      <dl className="mt-3 space-y-1 text-sm text-slate-400">
        <div className="flex justify-between">
          <dt>Movies</dt>
          <dd className="text-slate-200">{profile.cluster_size}</dd>
        </div>
        <div className="flex justify-between">
          <dt>Average rating</dt>
          <dd className="text-slate-200">
            {profile.average_rating ?? '—'}
          </dd>
        </div>
        <div className="flex justify-between">
          <dt>Silhouette score</dt>
          <dd className="text-slate-200">{profile.silhouette_score}</dd>
        </div>
      </dl>
    </Card>
  )
}

export function RuleTable({ rules }) {
  if (!rules?.length) return null
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-left text-sm">
        <thead>
          <tr className="border-b border-slate-700 text-slate-400">
            <th className="py-2 pr-4 font-medium">Pattern</th>
            <th className="py-2 pr-4 text-right font-medium">
              <span className="metric-help" title="How frequently the pattern occurs.">
                Support
              </span>
            </th>
            <th className="py-2 pr-4 text-right font-medium">
              <span
                className="metric-help"
                title="How often the consequent occurs when the antecedent occurs."
              >
                Confidence
              </span>
            </th>
            <th className="py-2 text-right font-medium">
              <span
                className="metric-help"
                title="How much stronger the relationship is compared with chance independence."
              >
                Lift
              </span>
            </th>
          </tr>
        </thead>
        <tbody>
          {rules.map((rule, index) => (
            <tr
              key={`${rule.antecedent}-${rule.consequent}-${index}`}
              className="border-b border-slate-800/70 last:border-0"
            >
              <td className="py-2.5 pr-4 text-slate-200">
                {rule.antecedent} <span className="text-amber-400">→</span>{' '}
                {rule.consequent}
              </td>
              <td className="py-2.5 pr-4 text-right text-slate-300">
                {(rule.support * 100).toFixed(1)}%
              </td>
              <td className="py-2.5 pr-4 text-right text-slate-300">
                {(rule.confidence * 100).toFixed(1)}%
              </td>
              <td className="py-2.5 text-right text-slate-300">
                {rule.lift.toFixed(2)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export function ProbabilityList({ probabilities }) {
  if (!probabilities?.length) return null
  return (
    <ul className="space-y-3">
      {probabilities.map((item) => {
        const percent = Math.round(item.probability * 100)
        return (
          <li key={item.genre}>
            <div className="flex items-baseline justify-between text-sm">
              <span className="text-slate-300">{item.genre}</span>
              <span className="font-medium text-slate-100">{percent}%</span>
            </div>
            <div className="mt-1 h-2 w-full overflow-hidden rounded-full bg-slate-800">
              <div
                className="h-full rounded-full bg-amber-500"
                style={{ width: `${percent}%` }}
              />
            </div>
          </li>
        )
      })}
    </ul>
  )
}
