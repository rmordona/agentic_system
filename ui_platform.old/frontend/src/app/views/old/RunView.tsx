// -----------------------------------------------------------------------------
// Project: Agentic System UI Platform
// File: src/app/views/RunView.tsx
//
// Description:
//   View for inspecting a specific run within a workspace.
//   Shows observability, stages, and runtime output.
// -----------------------------------------------------------------------------

import React from 'react'
import { useParams } from 'react-router-dom'

// Layout components
import TopBar from '../layout/TopBar'
import SideBar from '../layout/SideBar'
import MainPanel from '../layout/MainPanel'

// Observability components
import RunTimeline from '../observability/RunTimeline'
import StageStatus from '../observability/StageStatus'

// Chat or output component (could show logs, AI output, etc.)
import ChatWindow from '../chat/ChatWindow' // for default export

const RunView: React.FC = () => {
  const { workspaceId } = useParams<{ workspaceId: string }>()

  return (
    <div className="flex flex-col h-screen bg-gray-50 dark:bg-gray-900">
      {/* Top Bar */}
      <TopBar title={`Workspace ${workspaceId} - Run Viewer`} />

      <div className="flex flex-1 overflow-hidden">
        {/* Left Sidebar: Run list / navigation */}
        <SideBar className="w-64 bg-white dark:bg-gray-800">
          {/* Could include a list of runs */}
        </SideBar>

        {/* Main Panel: Run output / chat / logs */}
        <MainPanel className="flex-1 p-4 bg-gray-100 dark:bg-gray-900 overflow-auto">
          <ChatWindow workspaceId={workspaceId!} />
        </MainPanel>

        {/* Right Sidebar: Observability */}
        <SideBar className="w-80 bg-white dark:bg-gray-800 flex flex-col divide-y divide-gray-200 dark:divide-gray-700">
          <div className="p-2 overflow-auto">
            <RunTimeline workspaceId={workspaceId!} />
            <StageStatus workspaceId={workspaceId!} />
          </div>
        </SideBar>
      </div>
    </div>
  )
}

export default RunView

