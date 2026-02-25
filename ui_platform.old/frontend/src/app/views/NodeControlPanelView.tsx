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
    <div className="absolute inset-x-0 top-6 z-50 flex justify-center pointer-events-none">
      <div
        className="w-[80%] rounded-xl shadow-xl border pointer-events-auto"
        style={{
          backgroundColor: '#9a9a9a',
          borderColor: '#7f7f7f',
          color: '#1f1f1f',
        }}
      >
        {/* Navigation Tabs */}
        <nav
          className="flex justify-between gap-4 px-6 py-2 rounded-t-xl border-b"
          style={{
            backgroundColor: '#8a8a8a',
            borderColor: '#6f6f6f',
          }}
        >
          {(['Profile', 'Context', 'Resources', 'Specifications'] as Tab[]).map((tab) => (
            <button
              key={tab}
              className="px-4 py-2 text-sm font-semibold rounded-md transition-colors"
              style={{
                backgroundColor: activeTab === tab ? '#6f6f6f' : 'transparent',
                color: activeTab === tab ? '#ffffff' : '#2a2a2a',
              }}
              onClick={() => setActiveTab(tab)}
            >
              {tab}
            </button>
          ))}
        </nav>

        {/* Content */}
        <div
          className="p-6 h-[420px] overflow-y-auto"
          style={{ backgroundColor: '#9a9a9a' }}
        >

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

          {!isNode && (
            <div>
              <h3 className="font-bold mb-2">Edge ID</h3>
              <p className="text-sm mb-1">{selectedElement.id}</p>
              <p className="text-sm">Input: {selectedElement.data?.input}</p>
              <p className="text-sm">Output: {selectedElement.data?.output}</p>
            </div>
          )}
        </div>

        {/* Footer */}
        <div
          className="px-6 py-3 text-right rounded-b-xl border-t"
          style={{
            backgroundColor: '#8a8a8a',
            borderColor: '#6f6f6f',
          }}
        >
          <button
            className="px-4 py-1.5 rounded text-sm text-white"
            style={{ backgroundColor: '#b91c1c' }}
            onClick={() => setSelectedElement(null)}
          >
            Close
          </button>
        </div>
      </div>
    </div>
  )
}

export default NodeControlPanelView
