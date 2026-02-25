// File: src/app/components/NodeSpecificationView.tsx
import React from 'react'
import { Node } from 'reactflow'

interface NodeSpecificationViewProps {
  node: Node
  setNodes: React.Dispatch<React.SetStateAction<Node[]>>
}

const NodeSpecificationView: React.FC<NodeSpecificationViewProps> = ({ node, setNodes }) => {
  return (
    <div>
      <p className="text-sm mb-2">Specifications for node <strong>{node.data.label}</strong></p>
      <textarea
        value={node.data.specifications || ''}
        className="w-full p-1 rounded text-black"
        onChange={(e) =>
          setNodes((nds) =>
            nds.map((n) =>
              n.id === node.id ? { ...n, data: { ...n.data, specifications: e.target.value } } : n
            )
          )
        }
      />
    </div>
  )
}

export default NodeSpecificationView

