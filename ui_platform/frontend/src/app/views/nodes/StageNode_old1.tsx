import React from 'react'
import { Handle, Position } from 'reactflow'
import AgentNode from './AgentNode'
import MemoryNode from './MemoryNode'
import LLMNode from './LLMNode'
import SkillMgrNode from './SkillsNode'
import '../../styles/stage-node.css'

interface StageNodeProps {
  id: string
  data: {
    stage: {
      id: string
      name: string
      description?: string
      allowed_agents: string[]
    }
    isActive: boolean
  }
  selected?: boolean
}

const StageNode: React.FC<StageNodeProps> = ({ id, data, selected = false }) => {
  const { stage, isActive } = data

  return (
    <div
      className={`stage-node ${selected ? 'is-selected' : ''}`}
      role="group"
      aria-labelledby={`${id}-title`}
      tabIndex={0}
    >
      {/* Title */}
      <div className="stage-node__title" id={`${id}-title`}>
        {stage.name}
      </div>

      {/* Description */}
      {stage.description && (
        <div className="stage-node__description">{stage.description}</div>
      )}

      {/* Internal neon edges */}
      <svg
        className={`stage-node__edges ${
          isActive ? 'is-active' : ''
        }`}
        viewBox="0 0 100 100"
        preserveAspectRatio="none"
        aria-hidden
      >
        {/* Model → Agent */}
        <path
          d="M 20 35 C 40 35, 40 50, 50 50"
          className="stage-edge"
        />

        {/* Memory → Agent */}
        <path
          d="M 20 65 C 40 65, 40 50, 50 50"
          className="stage-edge"
        />

        {/* Agent → Skills */}
        <path
          d="M 50 50 C 65 50, 65 50, 80 50"
          className="stage-edge"
        />
      </svg>

      {/* Children Layout */}
      <div className="stage-node__children">
        {/* Left column */}
        <div className="stage-node__left-column">
          <LLMNode id={`${stage.id}-model`} />
          <MemoryNode id={`${stage.id}-memory`} />
        </div>

        {/* Center */}
        <div className="stage-node__center">
          <AgentNode
            id={`${stage.id}-agent`}
            data={{
              fields: [
                {
                  label: 'Agents',
                  value: stage.allowed_agents.join(', ') || 'None',
                },
              ],
            }}
          />
        </div>

        {/* Right */}
        <div className="stage-node__right">
          <SkillsNode id={`${stage.id}-skills`} />
        </div>
      </div>

      {/* React Flow Handles (still fully functional) */}
      <Handle
        type="target"
        position={Position.Left}
        id={`${id}-target`}
        className="stage-node__handle"
      />
      <Handle
        type="source"
        position={Position.Right}
        id={`${id}-source`}
        className="stage-node__handle"
      />
    </div>
  )
}

export default StageNode
