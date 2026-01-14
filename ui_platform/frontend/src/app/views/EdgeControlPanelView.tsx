// File: src/app/components/EdgeControlPanelView.tsx
import React, { useState } from 'react'
import { Edge } from 'reactflow'

import EdgeHITLView from './EdgeHITLView'
import EdgeConditionView from './EdgeConditionView'
import EdgeSpecificationView from './EdgeSpecificationView'

interface EdgeControlPanelProps {
  edge: Edge
  setEdges: React.Dispatch<React.SetStateAction<Edge[]>>
  onClose: () => void
}

type Tab = 'HITL' | 'Condition' | 'Specification'

const EdgeControlPanelView: React.FC<EdgeControlPanelProps> = ({
  edge,
  setEdges,
  onClose,
}) => {
  const [activeTab, setActiveTab] = useState<Tab>('HITL')

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
        {/* Navigation */}
        <nav
          className="flex gap-4 px-6 py-2 rounded-t-xl border-b"
          style={{
            backgroundColor: '#8a8a8a',
            borderColor: '#6f6f6f',
          }}
        >
          {(['HITL', 'Condition', 'Specification'] as Tab[]).map((tab) => (
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
        <div className="p-6 h-[420px] overflow-y-auto">
          {activeTab === 'HITL' && (
            <EdgeHITLView edge={edge} setEdges={setEdges} />
          )}
          {activeTab === 'Condition' && (
            <EdgeConditionView edge={edge} setEdges={setEdges} />
          )}
          {activeTab === 'Specification' && (
            <EdgeSpecificationView edge={edge} setEdges={setEdges} />
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
            onClick={onClose}
          >
            Close
          </button>
        </div>
      </div>
    </div>
  )
}

export default EdgeControlPanelView

