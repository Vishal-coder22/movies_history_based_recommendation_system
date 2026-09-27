import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

const tooltipStyle = {
  background: '#0f172a',
  border: '1px solid #334155',
  borderRadius: 8,
  fontSize: 12,
}

export function RatingChart({ data, title, yLabel }) {
  if (!data?.length) return null
  return (
    <figure className="m-0">
      <figcaption className="mb-3 text-sm font-medium text-slate-300">{title}</figcaption>
      <div className="h-64">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} margin={{ top: 4, right: 8, left: -18, bottom: 0 }}>
            <CartesianGrid stroke="#1e293b" strokeDasharray="3 3" vertical={false} />
            <XAxis dataKey="label" tick={{ fill: '#94a3b8', fontSize: 12 }} />
            <YAxis
              allowDecimals={false}
              tick={{ fill: '#94a3b8', fontSize: 12 }}
              label={
                yLabel
                  ? {
                      value: yLabel,
                      angle: -90,
                      position: 'insideLeft',
                      fill: '#64748b',
                      fontSize: 12,
                    }
                  : undefined
              }
            />
            <Tooltip
              cursor={{ fill: '#1e293b55' }}
              contentStyle={tooltipStyle}
              labelStyle={{ color: '#e2e8f0' }}
            />
            <Bar dataKey="value" fill="#f59e0b" radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
      <p className="sr-only">
        {data.map((entry) => `${entry.label}: ${entry.value}`).join(', ')}
      </p>
    </figure>
  )
}
