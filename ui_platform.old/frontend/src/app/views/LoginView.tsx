// src/app/views/LoginView.tsx
import React from 'react'
import { useNavigate } from 'react-router-dom'

const LoginView: React.FC = () => {
  const navigate = useNavigate()

  const handleLogin = () => {
    // Set bypass flag for demo purposes
    localStorage.setItem('bypassAuth', 'true')
    navigate('/workspaces', { replace: true })
  }

  return (
    <div className="flex flex-col items-center justify-center h-screen bg-gray-800 text-white">
      <div className="bg-gray-900 p-8 rounded shadow-md w-full max-w-sm">
        <h1 className="text-2xl font-bold mb-6 text-center">Agentic System Login</h1>
        <input
          type="text"
          placeholder="Username"
          className="w-full p-2 mb-4 rounded text-black"
        />
        <input
          type="password"
          placeholder="Password"
          className="w-full p-2 mb-4 rounded text-black"
        />
        <button
          onClick={handleLogin}
          className="w-full py-2 px-4 bg-blue-600 hover:bg-blue-700 rounded"
        >
          Login (Bypass)
        </button>
        <p className="mt-4 text-sm text-gray-400">Reset password functionality coming soon.</p>
      </div>
    </div>
  )
}

export default LoginView
