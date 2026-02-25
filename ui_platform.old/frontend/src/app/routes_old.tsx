// -----------------------------------------------------------------------------
// Project: Agentic System UI Platform
// File: src/app/routes.tsx
//
// Description:
//   Production-ready routing for Agentic System UI Platform.
//
//   Features:
//     - Public vs Authenticated layouts
//     - Lazy-loaded views
//     - Route-level loaders for authentication & data fetching
//     - Clear separation of workspaceId and runId
// -----------------------------------------------------------------------------

import React, { lazy } from 'react'
import { RouteObject, Navigate } from 'react-router-dom'

// Layouts
import PublicLayout from '@/components/layout/PublicLayout'
import AuthLayout from '@/components/layout/AuthLayout'


// Route loaders
import { requireAuthLoader } from './loaders/requireAuth'
import { fetchWorkspaceLoader } from './loaders/WorkspaceLoader'
import { fetchRunLoader } from './loaders/RunLoader'

// -----------------------------------------------------------------------------
// Lazy-loaded Views
// -----------------------------------------------------------------------------
const LoginView = lazy(() => import('./views/LoginView'))
const WorkspaceView = lazy(() => import('./views/WorkspaceView'))
const WorkspaceDashboardView = lazy(() => import('./views/WorkspaceCardView'))
const RunView = lazy(() => import('./views/RunView'))
const GraphEditorView = lazy(() => import('./views/GraphEditorView'))
const NotFoundView = lazy(() => import('./views/NotFoundView'))

// -----------------------------------------------------------------------------
// Routes
// -----------------------------------------------------------------------------
export const routes: RouteObject[] = [
  // Public routes
  {
    path: '/login',
    element: <PublicLayout><LoginView /></PublicLayout>,
  },
  // Authenticated routes
  {
    path: '/',
    element: <AuthLayout />,
    loader: requireAuthLoader,
    children: [
      { index: true, element: <Navigate to="/workspaces" replace /> },
      {
      path: '/login',
      element: (
        <PublicLayout>
          <LoginView />
        </PublicLayout>
      )
      },
      {
        path: 'workspaces',
        element: <WorkspaceView />, // Lists all workspaces
      },
      {
        path: 'workspaces/:workspaceId',
        element: <WorkspaceDashboardView />,
        loader: fetchWorkspaceLoader, // Fetch workspace details
        children: [
          {
            path: 'runs/:runId',
            element: <RunView />,
            loader: fetchRunLoader, // Fetch run details
          },
          {
            path: 'graph',
            element: <GraphEditorView />,
          },
        ],
      },
    ],
  },
  // Catch-all for 404
  {
    path: '*',
    element: <NotFoundView />,
  },
]

