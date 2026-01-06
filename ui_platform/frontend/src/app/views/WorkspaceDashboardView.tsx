// WorkspaceDashboardView.tsx
import React, { Suspense } from 'react'
import { Outlet, useParams, NavLink } from 'react-router-dom'
import TopBar from '../../components/layout/TopBar'
import SideBar from '../../components/layout/SideBar'
import MainPanel from '../../components/layout/MainPanel'

const NestedRouteFallback = () => (
  <div className="flex items-center justify-center h-full text-gray-700 dark:text-gray-200">
    Loading nested view...
  </div>
)

const WorkspaceDashboardView: React.FC = () => {
  const { workspaceId } = useParams<{ workspaceId: string }>()

  return (
    <div className="flex flex-col h-screen">
      <TopBar title={`Workspace ${workspaceId}`} />

      <div className="flex flex-1 overflow-hidden">
        <SideBar className="w-64 bg-green-300">
          <nav className="flex flex-col p-4 space-y-2">
            <NavLink to={`/workspaces/${workspaceId}`} end>Overview</NavLink>
            <NavLink to={`/workspaces/${workspaceId}/runs/1`}>Run 1</NavLink>
            <NavLink to={`/workspaces/${workspaceId}/graph`}>Graph Editor</NavLink>
          </nav>
        </SideBar>

        <MainPanel className="flex-1 overflow-auto p-4 bg-orange-300">
          <Suspense fallback={<NestedRouteFallback />}>
            <Outlet />
          </Suspense>
        </MainPanel>
      </div>
    </div>
  )
}

export default WorkspaceDashboardView
