// File: src/app/components/EdgeHITLView.tsx
import React from 'react'
import { Edge } from 'reactflow'

interface EdgeHITLViewProps {
  edge: Edge
  setEdges: React.Dispatch<React.SetStateAction<Edge[]>>
}

const EdgeHITLView: React.FC<EdgeHITLViewProps> = ({ edge, setEdges }) => {
  const enabled = edge.data?.hitl ?? false

  return (
    <div>
      <h3 className="font-semibold mb-4">Human-in-the-Loop</h3>

      <label className="flex items-center gap-2 text-sm">
        <input
          type="checkbox"
          checked={enabled}
          onChange={(e) =>
            setEdges((eds) =>
              eds.map((ed) =>
                ed.id === edge.id
                  ? { ...ed, data: { ...ed.data, hitl: e.target.checked } }
                  : ed
              )
            )
          }
        />
        Require human approval for this transition
      </label>
    </div>
  )
}

export default EdgeHITLView

