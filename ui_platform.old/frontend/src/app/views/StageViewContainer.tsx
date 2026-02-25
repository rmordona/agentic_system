// src/views/StageViewContainer.tsx
import React, { useState, useEffect } from 'react'
import StepperNode from './nodes/StepperNode'
import StageView from './StageView'
import { Node, Edge } from 'reactflow'
import { BuiltGraph } from '@/components/graph/BuildGraphFromConfig'

import { WorkspaceContext } from '@/components/types/WorkspaceContext'

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

interface StageViewContainerProps {
  stages: BuiltGraph['stages']
  activeStageId: string | null
  onStageChange: (stageId: string) => void
  devMode?: boolean
  workspaceContext: WorkspaceContext
}



// Background colors for stage triaging
const stageColors = ['#3e6aa7ff', '#112712ff', '#2a160fff', '#8a1e85ff', '#065f46']

const StageViewContainer: React.FC<StageViewContainerProps> = ({
  stages,
  activeStageId,
  onStageChange,
  devMode = false,
  workspaceContext
}) => {
  // Auto-select first stage if none is active
  
  useEffect(() => {
    if (!activeStageId && stages.length > 0) {
      requestAnimationFrame(() => onStageChange(stages[0].id))
    }


  }, [stages, activeStageId, onStageChange])


  // ------------------------
  // Layout container
  // ------------------------
  return (
    <div
      style={{
        width: '98%',
        height: '95%',
        margin: '12px auto',
        position: 'relative',
        borderRadius: '12px',
        overflow: 'hidden',
        boxShadow: '0 0 30px rgba(0,255,255,0.3)',
        backgroundColor: '#111827',
        zIndex: 10,
      }}
    >
      {/* StepperNode Controls */}
      <StepperNode
        data={{
          stages: stages.map(s => ({ id: s.id, name: s.name })),
          initialStageId: activeStageId,
          onStageChange,
        }}
      />

      {/* Stage Views */}
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
          {/* Stage description */}
          {stage.description && (
            <div
              style={{
                marginTop: '70px', // leave space for StepperNode
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

          {/* StageView */}
          <div style={{ flex: 1, position: 'relative' }}>
            <StageView
              nodes={stage.nodes}
              edges={stage.edges}
              isActive={stage.id === activeStageId}
              style={{
                backgroundColor: stageColors[idx % stageColors.length],
                transition: 'all 0.3s ease',
                width: '100%',
                height: '100%',
                zIndex: 10,
              }}
              nodeTypes={nodeTypes}
              workspaceContext={workspaceContext}
            />
          </div>
        </div>
      ))}
    </div>
  )
}

export default StageViewContainer
