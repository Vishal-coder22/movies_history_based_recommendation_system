import { useEffect, useState } from 'react'
import { Navigate, Route, Routes } from 'react-router-dom'
import Navbar from './components/Navbar'
import api, { clearSession, getToken, getUser, saveSession } from './services/api'
import Analytics from './pages/Analytics'
import Cleaning from './pages/Cleaning'
import Dashboard from './pages/Dashboard'
import Login from './pages/Login'
import Mining from './pages/Mining'
import Movies from './pages/Movies'
import Recommendations from './pages/Recommendations'
import Register from './pages/Register'
import Upload from './pages/Upload'

export default function App() {
  const [user, setUser] = useState(() => (getToken() ? getUser() : null))
  const [backendDown, setBackendDown] = useState(false)

  useEffect(() => {
    let alive = true
    const check = async () => {
      try {
        await api.get('/health')
        if (alive) setBackendDown(false)
      } catch {
        if (alive) setBackendDown(true)
      }
    }
    check()
    const id = setInterval(check, 10000)
    return () => {
      alive = false
      clearInterval(id)
    }
  }, [])

  const signIn = (session) => {
    saveSession(session)
    setUser(session.user)
  }

  const signOut = () => {
    clearSession()
    setUser(null)
  }

  const offlineBanner = backendDown ? (
    <div className="border-b border-rose-700 bg-rose-950 px-6 py-2.5 text-center text-sm text-rose-100">
      Backend is not running — open PowerShell in{' '}
      <code className="rounded bg-rose-900/60 px-1.5 py-0.5">C:\Users\visha\moviesforfuture</code>{' '}
      and run <code className="rounded bg-rose-900/60 px-1.5 py-0.5">.\start.ps1</code>. Retrying
      every 10 seconds…
    </div>
  ) : null

  if (!user) {
    return (
      <div>
        {offlineBanner}
        <Routes>
          <Route path="/login" element={<Login onSignIn={signIn} />} />
          <Route path="/register" element={<Register onSignIn={signIn} />} />
          <Route path="*" element={<Navigate to="/login" replace />} />
        </Routes>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-slate-950">
      {offlineBanner}
      <Navbar user={user} onSignOut={signOut} />
      <main className="mx-auto max-w-6xl px-6 py-8">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/upload" element={<Upload />} />
          <Route path="/cleaning/:importId" element={<Cleaning />} />
          <Route path="/movies" element={<Movies />} />
          <Route path="/analytics" element={<Analytics />} />
          <Route path="/mining" element={<Mining />} />
          <Route path="/recommendations" element={<Recommendations />} />
          <Route path="/login" element={<Navigate to="/" replace />} />
          <Route path="/register" element={<Navigate to="/" replace />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
    </div>
  )
}
