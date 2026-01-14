// File: src/app/components/EdgeConditionView.tsx
import React from 'react'
import { Edge } from 'reactflow'

interface EdgeConditionViewProps {
  edge: Edge
  setEdges: React.Dispatch<React.SetStateAction<Edge[]>>
}

const EdgeConditionView: React.FC<EdgeConditionViewProps> = ({ edge, setEdges }) => {
  const condition = edge.data?.condition ?? ''

  return (
    <div>
      <h3 className="font-semibold mb-4">Edge Condition</h3>

      <label className="block text-sm mb-1">Expression</label>
      <input
        type="text"
        className="w-full p-2 rounded border"
        value={condition}
        onChange={(e) =>
          setEdges((eds) =>
            eds.map((ed) =>
              ed.id === edge.id
                ? { ...ed, data: { ...ed.data, condition: e.target.value } }
                : ed
            )
          )
        }
      />
      <p className="text-xs mt-2 opacity-75">
        Example: <code>context.score &gt; 0.8</code>
      </p>
    </div>
  )
}

export default EdgeConditionView

