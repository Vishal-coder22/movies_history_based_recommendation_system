import {
  Cell,
  Legend,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
} from 'recharts'

const COLORS = [
  '#f59e0b',
  '#38bdf8',
  '#34d399',
  '#f472b6',
  '#a78bfa',
  '#fb923c',
  '#22d3ee',
  '#facc15',
  '#4ade80',
  '#e879f9',
  '#60a5fa',
  '#f87171',
]

export function GenreChart({ data, title = 'Genre distribution' }) {
  if (!data?.length) return null
  return (
    <figure className="m-0">
      <figcaption className="mb-3 text-sm font-medium text-slate-300">{title}</figcaption>
      <div className="h-72">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={data}
              dataKey="value"
              nameKey="name"
              innerRadius={55}
              outerRadius={95}
              paddingAngle={2}
            >
              {data.map((entry, index) => (
                <Cell key={entry.name} fill={COLORS[index % COLORS.length]} />
              ))}
            </Pie>
            <Tooltip
              formatter={(value, name) => [`${value} movies`, name]}
              contentStyle={{
                background: '#0f172a',
                border: '1px solid #334155',
                borderRadius: 8,
                fontSize: 12,
              }}
            />
            <Legend wrapperStyle={{ fontSize: 12 }} />
          </PieChart>
        </ResponsiveContainer>
      </div>
      <p className="sr-only">
        {data.map((entry) => `${entry.name}: ${entry.value}`).join(', ')}
      </p>
    </figure>
  )
}
