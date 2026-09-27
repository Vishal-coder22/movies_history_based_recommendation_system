import { useState } from 'react'
import { Navigate, Route, Routes } from 'react-router-dom'
import Navbar from './components/Navbar'
import { clearSession, getToken, getUser, saveSession } from './services/api'
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

  const signIn = (session) => {
    saveSession(session)
    setUser(session.user)
  }

  const signOut = () => {
    clearSession()
    setUser(null)
  }

  if (!user) {
    return (
      <Routes>
        <Route path="/login" element={<Login onSignIn={signIn} />} />
        <Route path="/register" element={<Register onSignIn={signIn} />} />
        <Route path="*" element={<Navigate to="/login" replace />} />
      </Routes>
    )
  }

  return (
    <div className="min-h-screen bg-slate-950">
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
