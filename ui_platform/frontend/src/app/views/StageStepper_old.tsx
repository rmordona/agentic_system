import React from 'react'
import './stage-stepper.css'

interface Stage {
  id: string
  name: string
}

interface Props {
  stages: Stage[]
  activeStageId: string
  onStageChange: (id: string) => void
}

const StageStepper = ({ stages, activeStageId, onStageChange }: Props) => {
  return (
    <div className="stage-stepper">
      {stages.map((stage, index) => (
        <button
          key={stage.id}
          className={`stage-stepper__item ${
            stage.id === activeStageId ? 'is-active' : ''
          }`}
          onClick={() => onStageChange(stage.id)}
        >
          <span className="stage-stepper__index">{index + 1}</span>
          <span className="stage-stepper__label">{stage.name}</span>
        </button>
      ))}
    </div>
  )
}

export default StageStepper

