// src/app/views/GraphEditorView.tsx

import React from 'react'
import { useParams } from 'react-router-dom'
import ChatView from './ChatView'
import ReactFlowGraphView from './ReactFlowGraphView'

import 'reactflow/dist/style.css'


const GraphEditorView: React.FC<{ mode: 'user' | 'developer' }> = ({ mode }) => {
  
  const { workspaceId } = useParams<{ workspaceId: string }>()

  if (!workspaceId) {
    return (
      <div className="flex items-center justify-center h-full text-red-600 dark:text-red-400">
        Invalid workspace ID
      </div>
    )
  }

  return (
    <div className="flex h-full w-full bg-blue-50 dark:bg-blue-900 rounded-lg overflow-hidden">
      {/* Left Graph Controls */}
      <div className="w-64 bg-blue-100 dark:bg-blue-800 p-4 border-r dark:border-blue-700">
        <h3 className="font-semibold text-blue-900 dark:text-blue-100 mb-3">
          Graph Controls
        </h3>
        <ul className="space-y-2 text-sm text-blue-800 dark:text-blue-200">
          <li>Add Node</li>
          <li>Add Edge</li>
          <li>Validate Graph</li>
          <li>Save Graph</li>
        </ul>
      </div>

      {/* Graph Canvas */}
      <div className="flex-1 bg-white dark:bg-gray-900 p-6">
        <h2 className="text-2xl font-bold mb-4 text-gray-900 dark:text-gray-100">
          Graph Editor
        </h2>

        <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
          Workspace ID: <strong>{workspaceId}</strong>
        </p>

        <div className="h-full rounded-lg border-2 border-dashed border-gray-300 dark:border-gray-700 flex items-center justify-center">
          <span className="text-gray-500 dark:text-gray-400">
              <div className="flex-1 h-full p-4">
                <ReactFlowGraphView devMode={true} />
              </div>
          </span>
        </div>
      </div>
    </div>
  )
}

export default GraphEditorView
