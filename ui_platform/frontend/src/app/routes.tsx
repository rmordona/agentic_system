import React, { lazy, Suspense } from 'react'
import { createBrowserRouter, Navigate } from 'react-router-dom'

// Layouts
import PublicLayout from '@/components/layout/PublicLayout'
import AuthLayout from '@/components/layout/AuthLayout'

// Loaders
import { requireAuthLoader } from './loaders/AuthLoader'
import { fetchWorkspaceLoader } from './loaders/WorkspaceLoader'
import { fetchRunLoader } from './loaders/RunLoader'

// Error handling
import RouteErrorBoundary from '../app/errors/RouteErrorBoundary'

// -----------------------------------------------------------------------------
// Lazy-loaded views
// -----------------------------------------------------------------------------
const LoginView = lazy(() => import('./views/LoginView'))
const WorkspaceView = lazy(() => import('./views/WorkspaceView'))
const WorkspaceDashboardView = lazy(() => import('./views/WorkspaceDashboardView'))
const RunView = lazy(() => import('./views/RunView'))
const GraphEditorView = lazy(() => import('./views/GraphEditorView'))
const NotFoundView = lazy(() => import('./views/NotFoundView'))

// Fallback for Suspense
const LoadingFallback = () => (
  <div className="flex items-center justify-center h-screen text-gray-700 dark:text-gray-200">
    Loading...
  </div>
)

const CompositeWorkspaceError: React.FC = () => {
  const error = useRouteError()

  if (isRunError(error)) return <RouteErrorBoundary />
  if (isPermissionError(error)) return <NotFoundView />

  return <GenericWorkspaceError />
}

// -----------------------------------------------------------------------------
// Production-ready routes
// -----------------------------------------------------------------------------
export const routes = createBrowserRouter([
  // Public routes
  {
    path: '/login',
    element: (
      <PublicLayout>
        <Suspense fallback={<LoadingFallback />}>
          <LoginView />
        </Suspense>
      </PublicLayout>
    ),
  },

  // Authenticated routes
  {
    path: '/',
    element: <AuthLayout />,
    errorElement: <RouteErrorBoundary />,
    //loader: requireAuthLoader, // temporarily can return null for bypass
    children: [
      { index: true, element: <Navigate to="/workspaces" replace /> },

      // Workspace list
      {
        path: 'workspaces',
        element: (
          <Suspense fallback={<LoadingFallback />}>
            <WorkspaceView />
          </Suspense>
        ),
      },

      // Workspace dashboard with nested routes
      {
        path: 'workspaces/:workspaceId',
        element: (
          <Suspense fallback={<LoadingFallback />}>
            <WorkspaceDashboardView />
          </Suspense>
        ),
        // loader: fetchWorkspaceLoader, // optional; can bypass for now
        children: [
          { index: true, element: <div className="p-4 bg-green-200">Overview</div> },
          {
            path: 'runs/:runId',
            element: (
              <Suspense fallback={<LoadingFallback />}>
                <RunView />
              </Suspense>
            ),
            // loader: fetchRunLoader, // optional; can bypass for now
          },
          {
            path: 'graph',
            element: (
              <Suspense fallback={<LoadingFallback />}>
                <GraphEditorView />
              </Suspense>
            ),
          },
        ],
      },

      // Catch-all 404
      {
        path: '*',
        element: (
          <Suspense fallback={<LoadingFallback />}>
            <NotFoundView />
          </Suspense>
        ),
      },
    ],
  },
])