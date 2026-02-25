// StepperNode.tsx
import React, { useState, useEffect } from 'react'
import { Handle, Position, NodeProps } from 'reactflow'
import '../../styles/stepper-node.css'

interface Stage {
  id: string
  name: string
  description?: string
}

interface StepperNodeData {
  stages: Stage[]
  initialStageId?: string
  onStageChange?: (id: string) => void
}

const StepperNode: React.FC<NodeProps<StepperNodeData>> = ({
  data,
  isConnectable,
}) => {
  const { stages = [], initialStageId, onStageChange } = data
  const [activeStageId, setActiveStageId] = useState<string | undefined>(
    initialStageId ?? stages[0]?.id
  )

  useEffect(() => {
    if (initialStageId) setActiveStageId(initialStageId)
  }, [initialStageId])

  const handleBadgeClick = (id: string) => {
    setActiveStageId(id)
    onStageChange?.(id) // notify parent container
  }

  if (!stages.length)
    return (
      <div className="stepper-node">
        <div className="stepper-topbar empty">No stages available</div>
      </div>
    )

  return (
    <div className="stepper-node">
      {/* ───────── Topbar ───────── */}
      <div className="stepper-topbar">
        {stages.map(stage => {
          const isActive = stage.id === activeStageId
          return (
            <button
              key={stage.id}
              className={`stepper-badge ${isActive ? 'active' : ''}`}
              onClick={() => handleBadgeClick(stage.id)}
              aria-current={isActive ? 'step' : undefined}
              title={stage.description ?? ''}
            >
              {stage.name}
            </button>
          )
        })}
      </div>
    </div>
  )
}

export default StepperNode
