// src/app/routes/errors/RouteErrorBoundary.tsx

import React from 'react'
import {
  isRouteErrorResponse,
  useRouteError,
  Link,
} from 'react-router-dom'

const RouteErrorBoundary: React.FC = () => {
  const error = useRouteError()

  // HTTP-style errors (redirects, 404s, 500s)
  if (isRouteErrorResponse(error)) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center p-6 text-center">
        <h1 className="text-2xl font-bold mb-2">
          {error.status} — {error.statusText}
        </h1>

        {error.data?.message && (
          <p className="text-gray-600 mb-4">
            {error.data.message}
          </p>
        )}

        <Link
          to="/"
          className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
        >
          Go Home
        </Link>
      </div>
    )
  }

  // Unexpected JS errors
  if (error instanceof Error) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center p-6 text-center">
        <h1 className="text-2xl font-bold mb-2">
          Something went wrong
        </h1>
        <p className="text-red-600 mb-4">{error.message}</p>

        <Link
          to="/"
          className="px-4 py-2 bg-blue-600 text-white rounded"
        >
          Back to safety
        </Link>
      </div>
    )
  }

  // Fallback
  return (
    <div className="min-h-screen flex items-center justify-center">
      Unknown error
    </div>
  )
}

export default RouteErrorBoundary
