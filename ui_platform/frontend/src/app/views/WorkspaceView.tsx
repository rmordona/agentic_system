// File: src/app/views/WorkspaceView.tsx
import React from 'react'
import { useNavigate } from 'react-router-dom'
import { useWorkspaceStore } from '../../store/workspaceStore'
import WorkspaceCardView from './WorkspaceCardView'

const WorkspaceView: React.FC = () => {
  const navigate = useNavigate()
  const workspaces = useWorkspaceStore((state) => state.workspaces)

  const handleOpenWorkspace = (id: string) => {
    navigate(`/workspaces/${id}`)
  }

  return (
    <div className="h-full flex flex-col">
      <header className="mb-4">
        <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100">
          Workspaces
        </h2>
      </header>

      <section className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {workspaces.map((ws) => (
          <WorkspaceCardView
            key={ws.id}
            workspace={ws}
            onClick={() => handleOpenWorkspace(ws.id)}
          />
        ))}
      </section>
    </div>
  )
}

export default WorkspaceView
