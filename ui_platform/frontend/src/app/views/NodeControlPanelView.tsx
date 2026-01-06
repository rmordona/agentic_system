// File: src/app/components/NodeControlPanelView.tsx
import React, { useState } from 'react'
import { Node, Edge } from 'reactflow'

import NodeProfileView from './NodeProfileView'
import NodeContextView from './NodeContextView'
import NodeResourceView from './NodeResourceView'
import NodeSpecificationView from './NodeSpecificationView'

interface NodeControlPanelProps {
  selectedElement: Node | Edge | null
  nodes: Node[]
  edges: Edge[]
  setNodes: React.Dispatch<React.SetStateAction<Node[]>>
  setEdges: React.Dispatch<React.SetStateAction<Edge[]>>
  setSelectedElement: React.Dispatch<React.SetStateAction<Node | Edge | null>>
}

type Tab = 'Profile' | 'Context' | 'Resources' | 'Specifications'

const NodeControlPanelView: React.FC<NodeControlPanelProps> = ({
  selectedElement,
  nodes,
  edges,
  setNodes,
  setEdges,
  setSelectedElement,
}) => {
  const [activeTab, setActiveTab] = useState<Tab>('Profile')

  if (!selectedElement) return null

  const isNode = 'data' in selectedElement

  return (
    <div className="absolute top-4 right-4 z-50 w-96 bg-gray-800 text-white rounded-lg shadow-lg">
      {/* Navigation Tabs */}
      <nav className="flex border-b border-gray-700 justify-between px-2">
        {(['Profile', 'Context', 'Resources', 'Specifications'] as Tab[]).map((tab) => (
          <button
            key={tab}
            className={`px-4 py-2 text-sm font-semibold transition-colors rounded-md ${
              activeTab === tab ? 'bg-gray-700 text-yellow-400' : 'hover:bg-gray-700'
            }`}
            onClick={() => setActiveTab(tab)}
          >
            {tab}
          </button>
        ))}
      </nav>

      <div className="p-4 h-96 overflow-y-auto">
        {/* Render content based on active tab */}
        {activeTab === 'Profile' && isNode && (
          <NodeProfileView node={selectedElement} setNodes={setNodes} />
        )}
        {activeTab === 'Context' && isNode && (
          <NodeContextView node={selectedElement} setNodes={setNodes} />
        )}
        {activeTab === 'Resources' && isNode && (
          <NodeResourceView node={selectedElement} setNodes={setNodes} />
        )}
        {activeTab === 'Specifications' && isNode && (
          <NodeSpecificationView node={selectedElement} setNodes={setNodes} />
        )}

        {/* For edges, simple info view */}
        {!isNode && (
          <div>
            <h3 className="font-bold mb-2">Edge ID: {selectedElement.id}</h3>
            <p className="text-sm">Input: {selectedElement.data?.input}</p>
            <p className="text-sm">Output: {selectedElement.data?.output}</p>
          </div>
        )}
      </div>

      {/* Close Button */}
      <div className="border-t border-gray-700 p-2 text-right">
        <button
          className="bg-red-600 px-3 py-1 rounded hover:bg-red-700 text-sm"
          onClick={() => setSelectedElement(null)}
        >
          Close
        </button>
      </div>
    </div>
  )
}

export default NodeControlPanelView
