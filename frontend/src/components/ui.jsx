export function PageHeader({ title, subtitle }) {
  return (
    <div className="mb-6">
      <h1 className="text-2xl font-semibold text-slate-100">{title}</h1>
      {subtitle && <p className="mt-1 text-sm text-slate-400">{subtitle}</p>}
    </div>
  )
}

export function Card({ children, className = '' }) {
  return (
    <div className={`rounded-xl border border-slate-800 bg-slate-900 p-5 ${className}`}>
      {children}
    </div>
  )
}

export function SummaryCard({ label, value, hint }) {
  return (
    <Card>
      <p className="text-xs font-medium uppercase tracking-wide text-slate-500">{label}</p>
      <p className="mt-2 text-2xl font-semibold text-slate-100">{value}</p>
      {hint && <p className="mt-1 text-xs text-slate-500">{hint}</p>}
    </Card>
  )
}

export function EmptyState({ children }) {
  return (
    <Card className="text-center">
      <p className="text-sm text-slate-400">{children}</p>
    </Card>
  )
}

export function ErrorBanner({ children }) {
  if (!children) return null
  return (
    <div className="mb-4 rounded-lg border border-rose-800 bg-rose-950/50 px-4 py-3 text-sm text-rose-200">
      {children}
    </div>
  )
}

export function Spinner({ label }) {
  return (
    <div className="flex items-center gap-3 text-sm text-slate-400" role="status">
      <span className="h-4 w-4 animate-spin rounded-full border-2 border-slate-600 border-t-amber-400" />
      {label}
    </div>
  )
}

export function Button({ children, variant = 'primary', className = '', ...props }) {
  const styles = {
    primary:
      'bg-amber-500 text-slate-950 hover:bg-amber-400 disabled:bg-slate-700 disabled:text-slate-400',
    secondary:
      'border border-slate-700 text-slate-200 hover:border-slate-500 disabled:opacity-50',
    ghost: 'text-slate-400 hover:text-slate-100 disabled:opacity-50',
  }
  return (
    <button
      type="button"
      className={`rounded-md px-4 py-2 text-sm font-medium transition-colors disabled:cursor-not-allowed ${styles[variant]} ${className}`}
      {...props}
    >
      {children}
    </button>
  )
}
