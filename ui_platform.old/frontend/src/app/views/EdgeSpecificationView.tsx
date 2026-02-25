// File: src/app/components/EdgeSpecificationView.tsx
import React from 'react'
import { Edge } from 'reactflow'

interface EdgeSpecificationViewProps {
  edge: Edge
  setEdges: React.Dispatch<React.SetStateAction<Edge[]>>
}

const EdgeSpecificationView: React.FC<EdgeSpecificationViewProps> = ({
  edge,
  setEdges,
}) => {
  const spec = edge.data?.specification ?? ''

  return (
    <div>
      <h3 className="font-semibold mb-4">Edge Specification</h3>

      <textarea
        className="w-full p-2 rounded border min-h-[120px]"
        value={spec}
        onChange={(e) =>
          setEdges((eds) =>
            eds.map((ed) =>
              ed.id === edge.id
                ? { ...ed, data: { ...ed.data, specification: e.target.value } }
                : ed
            )
          )
        }
      />

      <p className="text-xs mt-2 opacity-75">
        Used for execution semantics, constraints, or documentation.
      </p>
    </div>
  )
}

export default EdgeSpecificationView

