import { NavLink, useNavigate } from 'react-router-dom'

const LINKS = [
  { to: '/', label: 'Dashboard' },
  { to: '/upload', label: 'Upload' },
  { to: '/movies', label: 'Movies' },
  { to: '/analytics', label: 'Analytics' },
  { to: '/mining', label: 'Mining' },
  { to: '/recommendations', label: 'Recommendations' },
]

export default function Navbar({ user, onSignOut }) {
  const navigate = useNavigate()

  const handleSignOut = () => {
    onSignOut()
    navigate('/login')
  }

  return (
    <header className="sticky top-0 z-10 border-b border-slate-800 bg-slate-950/95 backdrop-blur">
      <div className="mx-auto flex max-w-6xl flex-wrap items-center gap-x-8 gap-y-3 px-6 py-4">
        <span className="text-lg font-semibold tracking-wide text-amber-400">
          CineMine
        </span>
        <nav className="flex flex-wrap gap-x-5 gap-y-2" aria-label="Main">
          {LINKS.map((link) => (
            <NavLink
              key={link.to}
              to={link.to}
              end={link.to === '/'}
              className={({ isActive }) =>
                `text-sm transition-colors ${
                  isActive
                    ? 'font-medium text-amber-400'
                    : 'text-slate-400 hover:text-slate-100'
                }`
              }
            >
              {link.label}
            </NavLink>
          ))}
        </nav>
        <div className="ml-auto flex items-center gap-4">
          <span className="text-sm text-slate-400">{user.name}</span>
          <button
            type="button"
            onClick={handleSignOut}
            className="rounded-md border border-slate-700 px-3 py-1.5 text-sm text-slate-300 transition-colors hover:border-slate-500 hover:text-slate-100"
          >
            Logout
          </button>
        </div>
      </div>
    </header>
  )
}
