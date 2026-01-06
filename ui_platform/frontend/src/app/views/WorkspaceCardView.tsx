import React from 'react'
import { WorkspaceResponse } from '../../types'

interface WorkspaceCardProps {
  workspace: WorkspaceResponse
  onClick: () => void
}

export const WorkspaceCard: React.FC<WorkspaceCardProps> = ({ workspace, onClick }) => {
  return (
    <div
      onClick={onClick}
      className="cursor-pointer bg-white dark:bg-gray-800 p-4 rounded-lg shadow hover:shadow-lg transition"
    >
      <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100">{workspace.name}</h2>
      {workspace.description && (
        <p className="text-gray-700 dark:text-gray-300 mt-2">{workspace.description}</p>
      )}
      <p className="mt-2 text-sm text-gray-500 dark:text-gray-400">
        {workspace.is_deployed ? 'Deployed' : 'Not deployed'}
      </p>
    </div>
  )
}


export default WorkspaceCardView