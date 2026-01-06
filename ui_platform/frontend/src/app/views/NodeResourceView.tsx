// File: src/app/components/NodeResourceView.tsx
import React from 'react'
import { Node } from 'reactflow'

interface NodeResourceViewProps {
  node: Node
  setNodes: React.Dispatch<React.SetStateAction<Node[]>>
}

const NodeResourceView: React.FC<NodeResourceViewProps> = ({ node, setNodes }) => {
  return (
    <div>
      <p className="text-sm mb-2">Resources linked to node <strong>{node.data.label}</strong></p>
      <textarea
        value={node.data.resources || ''}
        className="w-full p-1 rounded text-black"
        onChange={(e) =>
          setNodes((nds) =>
            nds.map((n) =>
              n.id === node.id ? { ...n, data: { ...n.data, resources: e.target.value } } : n
            )
          )
        }
      />
    </div>
  )
}

export default NodeResourceView

