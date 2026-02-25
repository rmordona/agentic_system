// File: src/app/components/NodeContextView.tsx
import React from 'react'
import { Node } from 'reactflow'

interface NodeContextViewProps {
  node: Node
  setNodes: React.Dispatch<React.SetStateAction<Node[]>>
}

const NodeContextView: React.FC<NodeContextViewProps> = ({ node, setNodes }) => {
  return (
    <div>
      <p className="text-sm mb-2">Context for node <strong>{node.data.label}</strong></p>
      <textarea
        value={node.data.context || ''}
        className="w-full p-1 rounded text-black"
        onChange={(e) =>
          setNodes((nds) =>
            nds.map((n) =>
              n.id === node.id ? { ...n, data: { ...n.data, context: e.target.value } } : n
            )
          )
        }
      />
    </div>
  )
}

export default NodeContextView

