// src/app/views/RunView.tsx

import React from 'react'
import { useParams } from 'react-router-dom'
import ChatView from './ChatView'

const RunView: React.FC<{ mode: 'user' | 'developer' }> = ({ mode }) => {
  const { workspaceId, runId } = useParams<{ workspaceId: string; runId: string }>()

  if (!workspaceId || !runId) {
    return (
      <div className="flex items-center justify-center h-full text-red-600 dark:text-red-400">
        Invalid workspace or run ID
      </div>
    )
  }

  
  return (
    <div className="flex flex-col h-full w-full bg-purple-50 dark:bg-purple-900 rounded-lg p-6">
      <h2 className="text-2xl font-bold text-purple-800 dark:text-purple-200 mb-4">
        Run Viewer
      </h2>

      <div className="text-sm text-purple-700 dark:text-purple-300 mb-6">
        Workspace ID: <strong>{workspaceId}</strong> <br />
        Run ID: <strong>{runId}</strong>
      </div>

      <div className="flex-1 rounded-md bg-white dark:bg-gray-800 shadow-inner p-4 overflow-auto">
        <p className="text-gray-700 dark:text-gray-300">
          Run execution output, logs, observability, and live updates will render here.
        </p>
      </div>
      {/* Bottom Chat Bar */}
      <div className="h-80 border-t border-gray-300 dark:border-gray-700">
        <ChatView workspaceId={workspaceId} runId={runId} mode={mode} />
      </div>
    </div>
  )
}

export default RunView
