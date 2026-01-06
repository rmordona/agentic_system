// -----------------------------------------------------------------------------
// Project: Agentic System UI Platform
// File: src/app/views/GraphEditorView.tsx
//
// Description:
//   Developer view for editing graphs within a workspace.
//   Provides a full workspace layout with side panels, graph editor, and inspectors.
//
// -----------------------------------------------------------------------------

import React from 'react'
import { useParams } from 'react-router-dom'

// Layout components
import TopBar from '../layout/TopBar'
import SideBar from '../layout/SideBar'
import MainPanel from '../layout/MainPanel'

// Graph components
import GraphEditor from '../graph/GraphEditor'
import NodeInspector from '../graph/NodeInspector'
import EdgeInspector from '../graph/EdgeInspector'

// Observability components
import RunTimeline from '../observability/RunTimeline'
import StageStatus from '../observability/StageStatus'

const GraphEditorView: React.FC = () => {
  const { workspaceId } = useParams<{ workspaceId: string }>()

  return (
    <div className="flex flex-col h-screen bg-gray-50 dark:bg-gray-900">
      {/* Top Navigation Bar */}
      <TopBar title={`Graph Editor - Workspace ${workspaceId}`} />

      <div className="flex flex-1 overflow-hidden">
        {/* Left Sidebar: Workspace / Graph list */}
        <SideBar className="w-64 bg-white dark:bg-gray-800">
          {/* Could add workspace navigation or graph selection here */}
        </SideBar>

        {/* Main Panel: Graph Editor */}
        <MainPanel className="flex-1 relative bg-gray-100 dark:bg-gray-900">
          <GraphEditor workspaceId={workspaceId!} />
        </MainPanel>

        {/* Right Sidebar: Node/Edge Inspectors + Observability */}
        <SideBar className="w-80 bg-white dark:bg-gray-800 flex flex-col divide-y divide-gray-200 dark:divide-gray-700">
          <div className="flex-1 p-2 overflow-auto">
            <NodeInspector workspaceId={workspaceId!} />
            <EdgeInspector workspaceId={workspaceId!} />
          </div>
          <div className="p-2">
            <RunTimeline workspaceId={workspaceId!} />
            <StageStatus workspaceId={workspaceId!} />
          </div>
        </SideBar>
      </div>
    </div>
  )
}

export default GraphEditorView

