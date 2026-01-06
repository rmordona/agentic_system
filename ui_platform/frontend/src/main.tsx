// src/main.tsx
import React, { Suspense } from 'react'
import ReactDOM from 'react-dom/client'
import { RouterProvider } from 'react-router-dom'
import { routes } from './app/routes'

// Global CSS
import './app/styles/theme.css'

const root = document.getElementById('root')
if (!root) throw new Error('Root element not found')

ReactDOM.createRoot(root).render(
  <React.StrictMode>
    <Suspense
      fallback={
        <div className="min-h-screen flex items-center justify-center text-gray-700 dark:text-gray-200">
          Loading...
        </div>
      }
    >
      <RouterProvider router={routes} />
    </Suspense>
  </React.StrictMode>
)
