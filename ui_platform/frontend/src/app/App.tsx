// -----------------------------------------------------------------------------
// Project: Agentic System UI Platform
// File: ui_platform/frontend/src/app/App.tsx
//
// Description:
//   Root application component.
//
//   Responsibilities:
//     - Application bootstrapping
//     - Router initialization
//     - Global layout shell
//     - Suspense boundaries
//     - Top-level error resilience
//
//   This component intentionally avoids business logic.
// -----------------------------------------------------------------------------

import React, { Suspense } from 'react'
import { BrowserRouter, useRoutes } from 'react-router-dom'
import { routes } from './routes'

// -----------------------------------------------------------------------------
// Layout Shell
// -----------------------------------------------------------------------------

/**
 * Base layout shell.
 * Provides top bar, left panel, and main content area.
 */
const LayoutShell: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  return (
    <div className="app-root">
      {/* Top Bar */}
      <header className="app-topbar">
        <h1>Agentic Platform</h1>
      </header>

      <div className="app-body">
        {/* Left Navigation Panel */}
        <aside className="app-sidebar">
          {/* Sidebar content (workspaces, mode switch, etc.) */}
        </aside>

        {/* Main Content */}
        <main className="app-main">{children}</main>
      </div>
    </div>
  )
}

// -----------------------------------------------------------------------------
// Router Renderer
// -----------------------------------------------------------------------------

/**
 * Renders the route tree using React Router.
 */
const RouterView: React.FC = () => {
  const element = useRoutes(routes)
  return element
}

// -----------------------------------------------------------------------------
// Root App
// -----------------------------------------------------------------------------

/**
 * Application root.
 */
const App: React.FC = () => {
  return (
    <BrowserRouter>
      <LayoutShell>
        <Suspense fallback={<div>Loading…</div>}>
          <RouterView />
        </Suspense>
      </LayoutShell>
    </BrowserRouter>
  )
}

export default App
