// -----------------------------------------------------------------------------
// Project: Agentic System UI Platform
// File: src/app/views/NotFoundView.tsx
//
// Description:
//   Generic 404 page for unknown routes.
// -----------------------------------------------------------------------------

import React from 'react'
import { useNavigate } from 'react-router-dom'

const NotFoundView: React.FC = () => {
  const navigate = useNavigate()

  return (
    <div className="flex flex-col items-center justify-center h-screen bg-gray-50 dark:bg-gray-900 text-gray-900 dark:text-gray-100">
      <h1 className="text-6xl font-bold mb-4">404</h1>
      <p className="text-xl mb-8">Oops! The page you are looking for does not exist.</p>
      <button
        onClick={() => navigate('/')}
        className="px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white rounded-md shadow-md transition"
      >
        Go to Home
      </button>
    </div>
  )
}

export default NotFoundView

