// -----------------------------------------------------------------------------
// Project: Agentic System UI Platform
// File: src/main.tsx
//
// Description:
//   Entry point for the frontend React application.
//
//   Features:
//     - Global theme application (light/dark)
//     - React 18 root mounting
//     - React Router v6 integration with Suspense for lazy routes
//     - StrictMode for development
//     - Enterprise-ready error boundaries and logging
//
// Author: Raymond M.O. Ordona
// Created: 2026-01-05
// -----------------------------------------------------------------------------

import React, { Suspense } from "react"
import ReactDOM from "react-dom/client"
import { createBrowserRouter, RouterProvider } from "react-router-dom"
import { routes } from "./app/routes"

// Global CSS
import "./app/styles/theme.css"

// Theme utilities
import { applyTheme, getCurrentTheme } from "./app/styles/theme"

// -----------------------------------------------------------------------------
// Apply persisted theme or fallback to default
// -----------------------------------------------------------------------------
const savedTheme = localStorage.getItem("theme")
const initialTheme = savedTheme || getCurrentTheme()
applyTheme(initialTheme)

// -----------------------------------------------------------------------------
// Helper: Global Error Boundary for Enterprise UX
// -----------------------------------------------------------------------------
const RootErrorBoundary: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  return (
    <React.ErrorBoundary
      fallbackRender={({ error, resetErrorBoundary }) => (
        <div className="min-h-screen flex flex-col items-center justify-center p-4 bg-red-50 dark:bg-red-900 text-red-900 dark:text-red-50">
          <h1 className="text-2xl font-bold mb-2">Something went wrong</h1>
          <p className="mb-4">{error.message}</p>
          <button
            className="px-4 py-2 bg-red-500 text-white rounded hover:bg-red-600"
            onClick={() => resetErrorBoundary()}
          >
            Retry
          </button>
        </div>
      )}
    >
      {children}
    </React.ErrorBoundary>
  )
}

// -----------------------------------------------------------------------------
// Create Router
// -----------------------------------------------------------------------------
const router = createBrowserRouter(routes)

// -----------------------------------------------------------------------------
// Mount the React application
// -----------------------------------------------------------------------------
const rootElement = document.getElementById("root")
if (!rootElement) {
  throw new Error(
    "Root element not found. Please add <div id='root'></div> in index.html"
  )
}

ReactDOM.createRoot(rootElement).render(
  <React.StrictMode>
    <RootErrorBoundary>
      <Suspense
        fallback={
          <div className="min-h-screen flex items-center justify-center text-gray-700 dark:text-gray-200">
            Loading...
          </div>
        }
      >
        <RouterProvider router={router} />
      </Suspense>
    </RootErrorBoundary>
  </React.StrictMode>
)
