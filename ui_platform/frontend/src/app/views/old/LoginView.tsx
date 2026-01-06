// -----------------------------------------------------------------------------
// Project: Agentic System UI Platform
// File: src/app/views/LoginView.tsx
//
// Description:
//   Customer-facing login page with temporary auth bypass.
// -----------------------------------------------------------------------------

import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { login } from '../auth/authService'

const LoginView: React.FC = () => {
  const navigate = useNavigate()

  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [showReset, setShowReset] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    setLoading(true)

    try {
      await login(username, password)
      navigate('/workspaces')
    } catch (err: any) {
      setError(err.message || 'Login failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="w-full">
      <h1 className="text-2xl font-semibold text-gray-900 dark:text-gray-100 mb-2">
        Sign in to Agentic Platform
      </h1>

      <p className="text-sm text-gray-600 dark:text-gray-400 mb-6">
        Manage your workspaces and agent executions
      </p>

      {error && (
        <div className="mb-4 rounded-md bg-red-50 dark:bg-red-900/30 p-3 text-sm text-red-700 dark:text-red-300">
          {error}
        </div>
      )}

      {!showReset ? (
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-1">
              Username
            </label>
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="w-full rounded-md border px-3 py-2 bg-white dark:bg-gray-800"
              placeholder="you@company.com"
              autoFocus
            />
          </div>

          <div>
            <label className="block text-sm font-medium mb-1">
              Password
            </label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full rounded-md border px-3 py-2 bg-white dark:bg-gray-800"
              placeholder="••••••••"
            />
          </div>

          <div className="flex items-center justify-between text-sm">
            <button
              type="button"
              onClick={() => setShowReset(true)}
              className="text-blue-600 hover:underline"
            >
              Forgot password?
            </button>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full rounded-md bg-blue-600 hover:bg-blue-700 text-white py-2 font-medium transition disabled:opacity-60"
          >
            {loading ? 'Signing in…' : 'Sign In'}
          </button>
        </form>
      ) : (
        <div className="space-y-4">
          <p className="text-sm text-gray-600 dark:text-gray-400">
            Password reset is not enabled yet.
            <br />
            Please contact your administrator.
          </p>

          <button
            onClick={() => setShowReset(false)}
            className="text-blue-600 hover:underline text-sm"
          >
            Back to login
          </button>
        </div>
      )}
    </div>
  )
}

export default LoginView

