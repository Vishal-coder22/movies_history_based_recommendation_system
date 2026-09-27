import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Button, Card, ErrorBanner } from '../components/ui'
import api, { errorMessage } from '../services/api'

export default function Login({ onSignIn }) {
  const navigate = useNavigate()
  const [form, setForm] = useState({ email: '', password: '' })
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  const update = (field) => (event) =>
    setForm((prev) => ({ ...prev, [field]: event.target.value }))

  const submit = async (event) => {
    event.preventDefault()
    setError('')
    if (!form.email.trim()) return setError('Please enter your email address.')
    if (!form.password) return setError('Please enter your password.')

    setBusy(true)
    try {
      const { data } = await api.post('/auth/login', {
        email: form.email.trim(),
        password: form.password,
      })
      onSignIn(data)
      navigate('/')
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-950 px-4">
      <Card className="w-full max-w-md">
        <h1 className="text-2xl font-semibold text-amber-400">CineMine</h1>
        <p className="mt-1 text-sm text-slate-400">Sign in to your account</p>
        <ErrorBanner>{error}</ErrorBanner>
        <form onSubmit={submit} className="mt-6 space-y-4" noValidate>
          <div>
            <label htmlFor="email" className="block text-sm font-medium text-slate-300">
              Email
            </label>
            <input
              id="email"
              type="email"
              autoComplete="email"
              value={form.email}
              onChange={update('email')}
              className="mt-1 w-full rounded-md border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-100 outline-none focus:border-amber-500"
            />
          </div>
          <div>
            <label htmlFor="password" className="block text-sm font-medium text-slate-300">
              Password
            </label>
            <input
              id="password"
              type="password"
              autoComplete="current-password"
              value={form.password}
              onChange={update('password')}
              className="mt-1 w-full rounded-md border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-100 outline-none focus:border-amber-500"
            />
          </div>
          <Button type="submit" disabled={busy} className="w-full">
            {busy ? 'Signing in…' : 'Login'}
          </Button>
        </form>
        <p className="mt-4 text-sm text-slate-400">
          No account yet?{' '}
          <Link to="/register" className="text-amber-400 hover:text-amber-300">
            Register
          </Link>
        </p>
      </Card>
    </div>
  )
}
