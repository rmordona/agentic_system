// File: src/app/components/NodeProfileView.tsx
import React from 'react'
import { Node } from 'reactflow'

interface NodeProfileViewProps {
  node: Node
  setNodes: React.Dispatch<React.SetStateAction<Node[]>>
}

const NodeProfileView: React.FC<NodeProfileViewProps> = ({ node, setNodes }) => {
  return (
    <div>
      <label className="block text-sm mb-1">Label</label>
      <input
        type="text"
        value={node.data.label}
        className="w-full p-1 rounded text-black mb-2"
        onChange={(e) =>
          setNodes((nds) =>
            nds.map((n) =>
              n.id === node.id ? { ...n, data: { ...n.data, label: e.target.value } } : n
            )
          )
        }
      />

      <label className="block text-sm mb-1">Description</label>
      <textarea
        value={node.data.description || ''}
        className="w-full p-1 rounded text-black"
        onChange={(e) =>
          setNodes((nds) =>
            nds.map((n) =>
              n.id === node.id ? { ...n, data: { ...n.data, description: e.target.value } } : n
            )
          )
        }
      />
    </div>
  )
}

export default NodeProfileView

