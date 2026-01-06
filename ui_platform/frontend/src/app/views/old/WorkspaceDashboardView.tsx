// -----------------------------------------------------------------------------
// Project: Agentic System UI Platform
// File: src/app/views/WorkspaceDashboardView.tsx
//
// Description:
//   Workspace Dashboard page for authenticated users.
//   - Renders workspace header (TopBar)
//   - Provides a sidebar for workspace navigation
//   - MainPanel renders nested routes (Runs, Graph Editor)
//   - Fully responsive and production-ready
//
//    WorkspaceDashboardView (route: /workspaces/:workspaceId)
//    ├─ TopBar (workspace title, actions)
//    ├─ SideBar (navigation: Overview / Runs / Graph)
//    ├─ MainPanel
//    │  └─ <Outlet /> (nested route: RunView, GraphEditorView)
//
// -----------------------------------------------------------------------------

import React, { Suspense } from 'react'
import { useParams, Outlet, NavLink } from 'react-router-dom'

// Layout components
import TopBar from '../components/layout/TopBar'
import SideBar from '../components/layout/SideBar'
import MainPanel from '../components/layout/MainPanel'

// Loading fallback for nested routes
const NestedRouteFallback: React.FC = () => (
  <div className="flex items-center justify-center h-full text-gray-700 dark:text-gray-200">
    Loading workspace details...
  </div>
)

const WorkspaceDashboardView: React.FC = () => {
  const { workspaceId } = useParams<{ workspaceId: string }>()

  if (!workspaceId) {
    return (
      <div className="flex items-center justify-center h-screen text-red-600 dark:text-red-400">
        Invalid workspace ID
      </div>
    )
  }

  return (
    <div className="flex flex-col h-screen bg-gray-50 dark:bg-gray-900 text-gray-900 dark:text-gray-50">
      {/* Top Navigation Bar */}
      <TopBar title={`Workspace ${workspaceId}`} />

      <div className="flex flex-1 overflow-hidden">
        {/* Left Sidebar */}
        <SideBar className="w-64 bg-white dark:bg-gray-800 border-r dark:border-gray-700">
          <nav className="flex flex-col p-4 space-y-2">
            <NavLink
              to={`/workspaces/${workspaceId}`}
              className={({ isActive }) =>
                `px-3 py-2 rounded-md hover:bg-gray-100 dark:hover:bg-gray-700 ${
                  isActive ? 'bg-gray-200 dark:bg-gray-700 font-semibold' : ''
                }`
              }
              end
            >
              Overview
            </NavLink>

            <NavLink
              to={`/workspaces/${workspaceId}/runs/`}
              className={({ isActive }) =>
                `px-3 py-2 rounded-md hover:bg-gray-100 dark:hover:bg-gray-700 ${
                  isActive ? 'bg-gray-200 dark:bg-gray-700 font-semibold' : ''
                }`
              }
            >
              Runs
            </NavLink>

            <NavLink
              to={`/workspaces/${workspaceId}/graph`}
              className={({ isActive }) =>
                `px-3 py-2 rounded-md hover:bg-gray-100 dark:hover:bg-gray-700 ${
                  isActive ? 'bg-gray-200 dark:bg-gray-700 font-semibold' : ''
                }`
              }
            >
              Graph Editor
            </NavLink>
          </nav>
        </SideBar>

        {/* Main Content Panel */}
        <MainPanel className="flex-1 overflow-auto p-4">
          <Suspense fallback={<NestedRouteFallback />}>
            {/* Nested routes like RunView or GraphEditorView render here */}
            <Outlet />
          </Suspense>
        </MainPanel>
      </div>
    </div>
  )
}

export default WorkspaceDashboardView

