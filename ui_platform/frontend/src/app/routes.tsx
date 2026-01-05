// -----------------------------------------------------------------------------
// Project: Agentic System UI Platform
// File: ui_platform/frontend/src/app/routes.tsx
//
// Description:
//   Application routing configuration.
//
//   Responsibilities:
//     - Route definitions
//     - Lazy loading of views
//     - Auth-protected routes
//     - Developer vs User mode gating
//
//   Uses React Router v6+
// -----------------------------------------------------------------------------

import React, { lazy } from 'react'
import { Navigate, RouteObject } from 'react-router-dom'
import { isAuthenticated, isDeveloperMode } from './auth'

// -----------------------------------------------------------------------------
// Lazy-loaded Views
// -----------------------------------------------------------------------------

const LoginView = lazy(() => import('../views/LoginView'))
const WorkspaceView = lazy(() => import('../views/WorkspaceView'))
const GraphEditorView = lazy(() => import('../views/GraphEditorView'))
const RunView = lazy(() => import('../views/RunView'))
const NotFoundView = lazy(() => import('../views/NotFoundView'))

// -----------------------------------------------------------------------------
// Route Guards
// -----------------------------------------------------------------------------

/**
 * Require authentication to access a route.
 */
function requireAuth(element: JSX.Element): JSX.Element {
  return isAuthenticated() ? element : <Navigate to="/login" replace />
}

/**
 * Require developer mode for advanced tooling.
 */
function requireDeveloperMode(element: JSX.Element): JSX.Element {
  if (!isAuthenticated()) {
    return <Navigate to="/login" replace />
  }
  if (!isDeveloperMode()) {
    return <Navigate to="/workspaces" replace />
  }
  return element
}

// -----------------------------------------------------------------------------
// Route Definitions
// -----------------------------------------------------------------------------

/**
 * Central route table for the application.
 */
export const routes: RouteObject[] = [
  {
    path: '/',
    element: <Navigate to="/workspaces" replace />,
  },
  {
    path: '/login',
    element: <LoginView />,
  },
  {
    path: '/workspaces',
    element: requireAuth(<WorkspaceView />),
  },
  {
    path: '/workspaces/:workspaceId',
    element: requireAuth(<RunView />),
  },
  {
    path: '/workspaces/:workspaceId/graph',
    element: requireDeveloperMode(<GraphEditorView />),
  },
  {
    path: '*',
    element: <NotFoundView />,
  },
]
