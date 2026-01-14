import React, { useState, useEffect } from 'react'
import StepperNode from './nodes/StepperNode'
import StageView from './StageView'
import { Node, Edge } from 'reactflow'

import AgentNode from './nodes/AgentNode'
import LLMNode from './nodes/LLMNode'
import MemoryNode from './nodes/MemoryNode'
import SkillsNode from './nodes/SkillsNode'

const nodeTypes = {
  AgentNode,
  LLMNode,
  MemoryNode,
  SkillsNode,
}

interface Stage {
  id: string
  name: string
  description?: string
  nodes: Node[]
  edges: Edge[]
}

interface StageViewsContainerProps {
  stages: Stage[]
}

// Background colors for triaging
const stageColors = ['#3e6aa7ff', '#112712ff', '#2a160fff', '#8a1e85ff', '#065f46']

const StageViewsContainer: React.FC<StageViewsContainerProps> = ({ stages }) => {
  const [activeStageId, setActiveStageId] = useState<string | null>(null)

  // Activate the first stage AFTER layout
  useEffect(() => {
    if (stages.length > 0) {
      requestAnimationFrame(() => setActiveStageId(stages[0].id))
    }
  }, [stages])

  if (!activeStageId) {
    return (
      <div style={{ width: '100%', height: '100%', position: 'relative' }}>
        <StepperNode
          data={{
            stages: stages.map(s => ({ id: s.id, name: s.name })),
            initialStageId: null,
            onStageChange: setActiveStageId,
          }}
        />
      </div>
    )
  }

  return (
    <div
      style={{
        width: '80%',
        height: '60%',
        margin: '20px auto',
        position: 'relative',
        borderRadius: '12px',
        overflow: 'hidden',
        boxShadow: '0 0 30px rgba(0,255,255,0.3)',
        backgroundColor: '#111827', 
        zIndex: 10
      }}
    >
      {/* Stepper controls */}
      <StepperNode
        data={{
          stages: stages.map(s => ({ id: s.id, name: s.name })),
          initialStageId: activeStageId,
          onStageChange: setActiveStageId,
        }}
      />

      {/* Stage views stacked */}
      {stages.map((stage, idx) => (
        <div
          key={stage.id}
          style={{
            display: stage.id === activeStageId ? 'flex' : 'none',
            flexDirection: 'column',
            width: '100%',
            height: '100%',
            position: 'absolute',
            top: 0,
            left: 0,
          }}
        >
          {/* Stage description at top */}
          {stage.description && (
            <div
              style={{
                marginTop: '70px', // adjust this to position below StepperNode
                padding: '8px 16px',
                fontSize: '14px',
                color: '#ffffffcc',
                backgroundColor: '#00000055',
                zIndex: 10,
              }}
            >
              {stage.description}
            </div>
          )}

          {/* StageView fills the remaining body */}
          <div style={{ flex: 1, position: 'relative' }}>
            <StageView
              nodes={stage.nodes}
              edges={stage.edges}
              isActive={true} // always active in this flex container
              style={{
                backgroundColor: stageColors[idx % stageColors.length],
                transition: 'all 0.3s ease',
                width: '100%',
                height: '100%',
                zIndex: 10
              }}
              nodeTypes={nodeTypes}
            />
          </div>

        </div>
      ))}
    </div>
  )
}

export default StageViewsContainer
